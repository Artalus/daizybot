#!/usr/bin/env python3

import time

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from selenium.webdriver.remote.webelement import WebElement as RemoteWebElement

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


    @staticmethod
    def from_selenium_element(article: RemoteWebElement, author: str):
        status = get_status(article, author)
        _, twid = status.split('/status/')
        txt_el: RemoteWebElement = next(d for d in article.find_elements_by_tag_name('div') if d.get_attribute('dir')=='auto' and d.get_attribute('lang')=='en')
        txt = txt_el.text
        return Twit(twid, txt, author)


    def __str__(self):
        return (
            f'{self.author} @ https://twitter.com/{self.author}/status/{self.twid}\n\n'
            f'{self.text}')

def tweets_from_string(html_doc, author):
    soup = BeautifulSoup(html_doc, 'html.parser')
    return (Twit.from_soup(tt, author) for tt in soup.select('div[class*="tweet-text"]'))

def href(e: RemoteWebElement):
    return e.get_attribute('href')

def get_status(article: RemoteWebElement, author: str):
    e = [x for x in article.find_elements_by_tag_name('a') if f'{author}/status/' in href(x)]
    if not e:
        return None
    return href(e[0])

def is_pinned_article(article: RemoteWebElement):
    svg_wrapper = next(x for x in article.find_elements_by_tag_name('div') if x.get_attribute('style').startswith('flex-basis'))
    if not svg_wrapper:
        return False
    svgs = svg_wrapper.find_elements_by_tag_name('svg')
    if not svgs:
        return False
    return True

def tweets_from_driver(driver: RemoteWebDriver, author: str):
    articles = driver.find_elements_by_tag_name('article')
    posts = [x for x in articles if get_status(x, author) and not is_pinned_article(x)]
    return [Twit.from_selenium_element(p, author) for p in posts]

class Scrapper:
    def __init__(self):
        chrome_options = webdriver.ChromeOptions()
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        self.driver: RemoteWebDriver = webdriver.Chrome(chrome_options=chrome_options)

    def scroll(self):
        SCROLL_PAUSE_TIME = 0.5
        # Get scroll height
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        for i in range(5):
            # Scroll down to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # Wait to load page
            time.sleep(SCROLL_PAUSE_TIME)
            # Calculate new scroll height and compare with last scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def tweets_from_web(self, author):
        self.driver.get(f'https://mobile.twitter.com/{author}')
        self.scroll()
        open('twitter_last.html', 'wb').write(self.driver.page_source.encode())
        twits = tweets_from_driver(self.driver, author)
        if not twits:
            logger().error('!! SOMETHING BAD HAPPENED WITH TWITTER !!')
            logger().error('SEE twitter_last.html FILE')
        return twits

def main():
    s = Scrapper()
    tweets = s.tweets_from_web('DayZ')
    for twit in tweets:
        print(twit)
        print('-'*20)
