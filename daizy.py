#!/usr/bin/env python3

import vk_api as vk
import vk_api.bot_longpoll as vkblp
import vk_api.longpoll as vklp
from vk_api.utils import get_random_id

import os
import json
import bisect
import re
import queue
import threading
import twit
import requests
import time
import traceback

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


def get_api():
    me = json.load(open('me.json'))
    apikey = me['apikey']
    group = me['group']

    v = vk.VkApi(token=apikey, api_version='5.101')
    api = v.get_api()
    gid = api.utils.resolveScreenName(screen_name=group)['object_id']
    bot = vkblp.VkBotLongPoll(v, group_id=gid)
    return bot, v, api, gid, me

bot, _, api, gid, me = get_api()
print(bot)
print(api)
print(gid)
print(me)

def json_or_default(jfile, default):
    if not os.path.isfile(jfile):
        return default
    return json.load(open(jfile))

SUBFILE='subscribers.json'
def get_subscribers():
    x = json_or_default(SUBFILE, [])
    assert isinstance(x, list)
    if x:
        assert isinstance(x[0], int)
    return x

def ensure_subscribers_relevant(subs, chunksize=20):
    for chunk in chunker(subs, chunksize):
        cs = len(chunk)
        x = api.messages.getConversations()
        if x['count'] != chunksize:
            if cs == 1:
                del subs[0]
            else:
                c2 = cs//2
                ensure_subscribers_relevant(subs[:c2], c2)
                ensure_subscribers_relevant(subs[c2:], c2)

subscribers = get_subscribers()


def add_subscriber(peer_id: int):
    if peer_id in subscribers:
        print(f'{peer_id} already subscribed; ignoring')
        return
    bisect.insort(subscribers, peer_id)
    with open(SUBFILE, 'w') as f:
        json.dump(subscribers, f)
def remove_subscriber(peer_id: int):
    if peer_id not in subscribers:
        print(f'{peer_id} not subscribed; ignoring')
        return
    subscribers.remove(peer_id)
    with open(SUBFILE, 'w') as f:
        json.dump(subscribers, f)


def send_to(peer_id, message):
    try:
        api.messages.send(
            peer_id=peer_id,
            random_id=get_random_id(),
            message=message
        )
    except vk.ApiError as e:
        print(f'Failed to send "{message[:100]}"... to {peer_id}:\n{e.error}')
        if e.code == 7:
            print('Permission denied, seems like bot was removed from this conversation')
            print(f'Removing {peer_id} from subscribers')
            remove_subscriber(peer_id)

COMMAND_RE = re.compile(fr'\[club{gid}\|.+?\] *\/(.+)')
def try_extract_command(msg):
    x = COMMAND_RE.search(msg)
    if x:
        return x.group(1)

def is_invitation(event):
    if 'action' in event.object and event.object.action['type'] == 'chat_invite_user':
        return True
    cmd = try_extract_command(event.object.text)
    if cmd and cmd == 'start':
        return True
    return False


def listen_for_messages():
    for e in bot.check():
        if e.type == vkblp.VkBotEventType.MESSAGE_NEW:
            yield e


def get_last_twits() -> dict:
    x = json_or_default('last_twits.json', {})
    assert(isinstance(x, dict))
    for a,b in x.items():
        assert(isinstance(a, str))
        assert(isinstance(b, int))
    return x

last_twits = get_last_twits()

def last_twit(author: str):
    if author in last_twits:
        return last_twits[author]
    return 0

def update_last_twit(author: str, twid: int):
    write = False
    if author not in last_twits:
        print(f'No known twits from {author}, adding {twid}')
        write = True
    elif twid > last_twits[author]:
        print(f'{twid} is newer for {author} than {last_twits[author]}, updating')
        write = True
    if write:
        last_twits[author] = twid
        json.dump(last_twits, open('last_twits.json', 'w'))


def new_twits(author: str):
    twits = []
    for t in twit.tweets_from_web(author):
        if t.twid > last_twit(author):
            twits.append(t)
        else:
            break
    if twits:
        update_last_twit(author, twits[0].twid)
    return twits


def main():
    if 'owner' in me:
        for chunk in chunker(subscribers, 20):
            ss = ', '.join(map(str, chunk))
            send_to(me['owner'], f'bot online in {ss}')

    while True:
        try:
            print('vk iteration...')
            for event in listen_for_messages():
                print(event)
                if is_invitation(event):
                    pi = event.object.peer_id
                    add_subscriber(pi)
                    send_to(pi, f'Added to {pi}')
            print('twitter iteration...')
            for twitch in chunker(new_twits(me['twitter']), 7):
                msg = f'\n\n{"-"*10}\n\n'.join(map(str, twitch))
                for sub in subscribers[:]:
                    send_to(sub, msg)
        except Exception as e:
            print('SOMETHING HAPPENED:')
            traceback.print_exc()
            print("sleeping...")
            time.sleep(30)


    print("finishing")

if __name__ == "__main__":
    main()
