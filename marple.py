#!/usr/bin/env python3
import re
from typing import List
from termcolor import colored
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from bs4 import BeautifulSoup as bs
import asyncio
import aiohttp


username_marks_symbols = '/.~=?&      -'

junk_regexps = [
    'ref_src=[^&]+',
    'via=[^&]+',
]

junk_end_symbols = '?&/'

links_blacklist = [
    'books.google.ru',
]


class Link:
    url: str
    title: str

    def __init__(self, url, title, username):
        self.url = url.lower()
        self.title = title
        self.name = username.lower()
        self.normalize()

    def __eq__(self, other):
        return self.url == other.url

    def __hash__(self):
        return hash(self.url)

    def __str__(self):
        return f'{self.title}({self.url})'

    def normalize(self):
        url = self.url
        for r in junk_regexps:
            url = re.sub(r, '', url)

        self.url = url.rstrip(junk_end_symbols)

    def username_profile_symbols(self):
        if self.name not in self.url:
            return '', ''

        left_symbol = self.url[self.url.index(self.name)-1]
        right_symbol = ''

        if len(self.url) > self.url.index(self.name)+len(self.name):
            right_symbol = self.url[self.url.index(self.name)+len(self.name)]

        return left_symbol, right_symbol

    # the less the junk score, the more likely it is profile url
    @property
    def junk_score(self):
        score = 0
        left_symbol, right_symbol = self.username_profile_symbols()
        for i in left_symbol+right_symbol:
            if i in username_marks_symbols:
                score += username_marks_symbols.index(i)

        return len(self.url) + score * 10

    def is_it_likely_username_profile(self):
        left_symbol, right_symbol = self.username_profile_symbols()

        return (left_symbol + right_symbol).strip(username_marks_symbols) == ''


def merge_links(links: List[Link], name: str, filter_by_urls: bool = True) -> List[Link]:
    name_filter = lambda l: name in l.url.lower()
    blacklist_filter = lambda l: not any([s in l.url.lower() for s in links_blacklist])

    if filter_by_urls:
        links = list(filter(name_filter, links))
    links = list(filter(blacklist_filter, links))

    return list(set(links))


class Parser:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:84.0) Gecko/20100101 Firefox/84.0'
    }

    async def request(self, url):
        session = aiohttp.ClientSession()
        coro = await session.get(url, headers=self.headers)
        response = await coro.text()
        await session.close()

        return response

    async def run(self, storage, username, count=100, lang='en'):
        url = self.make_url(username, count, lang)
        html = await self.request(url)
        results = await self.parse(html, username)

        storage += results


class GoogleParser(Parser):
    def make_url(self, username, count, lang):
        return 'https://www.google.com/search?q={}&num={}&hl={}'.format(username, count, lang)

    async def parse(self, html, username):
        results = []

        soup = bs(html, 'html.parser')
        result_block = soup.find_all('div', attrs={'class': 'g'})

        for result in result_block:
            link = result.find('a', href=True)
            title = result.find('h3')

            if link and title:
                results.append(Link(link['href'], title.text, username))

        return results


class DuckParser(Parser):
    def make_url(self, username, count, lang):
        return 'https://duckduckgo.com/html/?q={}'.format(username)

    async def parse(self, html, username):
        results = []

        soup = bs(html, 'html.parser')
        result_block = soup.find_all('a', class_='result__a', href=True)

        for result in result_block:
            link = result['href']
            title = result.text

            if link and title:
                results.append(Link(link, title, username))

        return results


def main():
    parser = ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter,
        description='Marple v0.0.1\n'
        'Collect links to profiles by username through search engines',
    )
    parser.add_argument(
        'username',
        help='Username to search by.',
    )
    parser.add_argument(
        '-t',
        '--threshold',
        action='store',
        type=int,
        default=100,
        help='Threshold to discard junk search results',
    )
    parser.add_argument(
        '--results-count',
        action='store',
        type=int,
        default=100,
        help='Count of results parsed from each search engine',
    )
    parser.add_argument(
        '--no-url-filter',
        action='store_false',
        dest='url_filter',
        default=True,
        help='Disable filtering results by usernames in URLs',
    )
    parser.add_argument(
        '--plugin',
        dest='plugins',
        default='',
        choices={'maigret'},
        help='Additional plugins to analyze links',
    )
    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        default=False,
        help='Display junk score for each result',
    )
    parser.add_argument(
        '-l',
        '--list',
        action='store_true',
        default=False,
        help='Display only list of all the URLs',
    )
    args = parser.parse_args()

    username = args.username
    parsers = [
        GoogleParser(),
        DuckParser(),
    ]

    results = []
    coros = [parser.run(results, username, args.results_count) for parser in parsers]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*coros))

    links = merge_links(results, username, args.url_filter)
    links = sorted(links, key=lambda x: x.junk_score)

    if args.plugins == 'maigret':
        try:
            import maigret
            db = maigret.MaigretDatabase().load_from_file(maigret.__path__[0]+'/resources/data.json')
            maigret.db = db
        except Exception as e:
            print(e)
            print('\tInstall maigret first!')
            print('\tpip3 install maigret')

    if args.list:
        for r in links:
            print(r.url)
        return

    for r in links:
        if r.is_it_likely_username_profile() and r.junk_score <= args.threshold:
            message = r.url

            if args.verbose:
                message = colored(f'[{r.junk_score}]', 'magenta') + ' ' + message

            if args.plugins == 'maigret' and maigret.db:
                if maigret.db.extract_ids_from_url(r.url):
                    message += colored(' [v] Maigret', 'green')
                else:
                    message += colored(' [ ] Maigret', 'yellow')

            print(f'{message}\n{r.title}\n')


if __name__ == '__main__':
    main()
