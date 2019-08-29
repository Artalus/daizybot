#!/usr/bin/env python3

import vk_api as vk
import vk_api.bot_longpoll as vkblp
import vk_api.longpoll as vklp
from vk_api.utils import get_random_id

import os
import json
import bisect
import re
import requests
import time
import traceback
import sys

import daizy.twit as twit
from daizy.util import init_logger, logger

from daizy.commands import CommandProcessor

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
    x = json_or_default(SUBFILE, dict())
    assert isinstance(x, dict)
    if x:
        assert isinstance(next(iter(x.values())), dict)
    return x

subscribers = get_subscribers()
print(subscribers)


def activate(peer_id: int, adder: int):
    sp = str(peer_id)
    if sp in subscribers:
        logger().info(f'{peer_id} already activated; ignoring')
        return
    subscribers[sp] = {"admins": [adder], "twitters": []}
    with open(SUBFILE, 'w') as f:
        json.dump(subscribers, f, indent=2)
    send_to(peer_id, "ok")
def deactivate(peer_id: int):
    sp = str(peer_id)
    if sp not in subscribers:
        logger().info(f'{peer_id} not activated; ignoring')
        return
    del subscribers[sp]
    with open(SUBFILE, 'w') as f:
        json.dump(subscribers, f, indent=2)
    send_to(peer_id, "ok")


def send_to(peer_id, message):
    try:
        api.messages.send(
            peer_id=peer_id,
            random_id=get_random_id(),
            message=message
        )
    except vk.ApiError as e:
        logger().warning(f'Failed to send "{message[:100]}"... to {peer_id}:\n{e.error}')
        if e.code == 7:
            logger().warning('Permission denied, seems like bot was removed from this conversation')
            logger().warning(f'Deactivating {peer_id}')
            deactivate(peer_id)

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
        logger().info(f'No known twits from {author}, adding {twid}')
        write = True
    elif twid > last_twits[author]:
        logger().info(f'{twid} is newer for {author} than {last_twits[author]}, updating')
        write = True
    if write:
        last_twits[author] = twid
        json.dump(last_twits, open('last_twits.json', 'w'), indent=2)


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

def all_twitters(subscribers):
    for s in subscribers.values():
        for t in s['twitters']:
            yield t


def main():
    init_logger()
    try:
        logger().info('Bot starting')

        if 'owner' in me:
            for chunk in chunker(list(subscribers.keys()), 20):
                ss = ', '.join(map(str, chunk))
                send_to(me['owner'], f'bot online in {ss}')

        while True:
            try:
                print('vk iteration...')
                for event in listen_for_messages():
                    logger().debug(event)
                    if is_invitation(event):
                        pi = event.object.peer_id
                        activate(pi)
                        send_to(pi, f'Added to {pi}')
                    else:
                        proc = CommandProcessor(api, event.object.peer_id)
                        cmd = try_extract_command(event.object.text)
                        if cmd:
                            if cmd.startswith('identify'):
                                proc.identify(cmd.split(' ')[1])
                print('twitter iteration...')
                for author in all_twitters(subscribers):
                    for twit in chunker(new_twits(author), 7):
                        msg = f'\n\n{"-"*10}\n\n'.join(map(str, twit))
                        for sub in list(subscribers.keys()):
                            send_to(sub, msg)
            except Exception as e:
                logger().error('SOMETHING HAPPENED:')
                logger().error(traceback.format_exc())
                logger().debug("sleeping...")
                time.sleep(30)
        print("finishing")
    except Exception as e:
        logger().critical('Daizy terminated with an exception:')
        logger().critical(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
        main()
