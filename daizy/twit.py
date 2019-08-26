#!/usr/bin/env python3

from bs4 import BeautifulSoup
import bs4
import requests

from daizy.util import logger


def tag_to_str(x):
    if isinstance(x, bs4.element.NavigableString):
        return str(x).strip()
    for a in ('data-expanded-url', 'data-url', 'href'):
        if x.has_attr(a):
            link = x[a]
            break
    lf = '\n'
    txt = ''
    if link[0] == '/':
        link = f'https://twitter.com{link}'
        lf = ' '
        txt = f' | {x.text.strip()}'
    if x.name == 'a':
        return '{lf}{}{}{lf}'.format(link, txt, lf=lf)
    return str(x)

class Twit:
    def __init__(self, twid: str, text: str, author: str):
        self.twid = int(twid)
        self.text = text.strip()
        self.author = author

    @staticmethod
    def from_soup(tt, author):
        twid = tt["data-id"]
        txt = tt.select('div[class*="dir-ltr"]')[0]
        message = ''
        for x in txt:
            message += tag_to_str(x)
        return Twit(twid, message, author)

    def __str__(self):
        return (
            f'{self.author} @ https://twitter.com/{self.author}/status/{self.twid}\n\n'
            f'{self.text}')

def tweets_from_string(html_doc, author):
    soup = BeautifulSoup(html_doc, 'html.parser')
    return (Twit.from_soup(tt, author) for tt in soup.select('div[class*="tweet-text"]'))

def tweets_from_web(author):
    content = requests.get(f'https://mobile.twitter.com/{author}').content
    open('twitter_last.html', 'w').write(content.decode('utf-8'))
    twits = tweets_from_string(content, author)
    if not twits:
        logger().error('!! SOMETHING BAD HAPPENED WITH TWITTER !!')
        logger().error('SEE twitter_last.html FILE')
    return twits

def main():
    tweets = tweets_from_string(open("twit/dayzf2.xml").read())
    tweets = tweets_from_web()
    for twit in tweets:
        print(twit)
        print('-'*20)

if __name__ == "__main__":
    main()
