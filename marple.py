#!/usr/bin/env python3
import json
import re
import os
from typing import List
from termcolor import colored
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from bs4 import BeautifulSoup as bs
import asyncio
import aiohttp
import requests

import yandex_search

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
        symbols_score = 0
        left_symbol, right_symbol = self.username_profile_symbols()
        for i in left_symbol+right_symbol:
            if i in username_marks_symbols:
                symbols_score += username_marks_symbols.index(i)

        name_index = self.name in self.url and self.url.index(self.name) * 3 or 0
        return len(self.url.split('?')[0]) + symbols_score * 10 + name_index

    def is_it_likely_username_profile(self):
        left_symbol, right_symbol = self.username_profile_symbols()

        return (left_symbol + right_symbol).strip(username_marks_symbols) == ''


class LinkEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Link):
            return obj.__dict__
        return json.JSONEncoder.default(self, obj)


def merge_links(links: List[Link], name: str, filter_by_urls: bool = True) -> List[Link]:
    name_filter = lambda l: name in l.url.lower()
    blacklist_filter = lambda l: not any([s in l.url.lower() for s in links_blacklist])

    if filter_by_urls:
        links = list(filter(name_filter, links))
    links = list(filter(blacklist_filter, links))

    return list(set(links))


async def extract(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:84.0) Gecko/20100101 Firefox/84.0'
    }
    session = aiohttp.ClientSession()
    coro = await session.get(url, headers=headers)
    response = await coro.text()
    await session.close()

    return response


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

        if not results:
            return f'Got no results from {self.name}'

        storage += results


class YandexParser:
    name = 'Yandex API search'

    """
        You should have env variables with user and key, e.g.

        export YANDEX_USER=user
        export YANDEX_KEY=key
    """
    async def run(self, storage, username, count=100, lang='en'):
        try:
            yandex = yandex_search.Yandex()
            results = yandex.search(username).items
        except Exception as e:
            return str(e)

        tuples_list = [Link(r["url"], r["title"], username) for r in results]

        storage += tuples_list


class GoogleParser(Parser):
    name = 'Google scraping'

    def __init__(self, quoted=False):
        self.quoted = quoted
        super().__init__()

    def make_url(self, username, count, lang):
        processed_username = username if not self.quoted else f'"{username}"'
        return 'https://www.google.com/search?q={}&num={}&hl={}'.format(processed_username, count, lang)

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
    name = 'DuckDuckGo scraping'

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


class MarpleResult:
    def __init__(self, results, links, errors, warnings):
        self.all_links = results
        self.unique_links = links
        self.errors = errors
        self.warnings = warnings


def marple(username, max_count, url_filter_enabled, is_debug=False):
    parsers = [
        GoogleParser(),
        DuckParser(),
        YandexParser(),
    ]

    results = []
    errors = []
    warnings = []

    debug_filename = f'debug_{username}.json'

    if not is_debug or not os.path.exists(debug_filename):
        coros = [parser.run(results, username, max_count) for parser in parsers]

        loop = asyncio.get_event_loop()
        errors = loop.run_until_complete(asyncio.gather(*coros))

        if is_debug:
            with open(debug_filename, 'w') as results_file:
                json.dump({'res': results}, results_file, cls=LinkEncoder)
    else:
        with open(debug_filename) as results_file:
            results = [Link(l['url'], l['title'], username) for l in json.load(results_file)['res']]

        warnings.append(colored(f'Links were loaded from file {debug_filename}!', 'yellow'))

    links = merge_links(results, username, url_filter_enabled)
    links = sorted(links, key=lambda x: x.junk_score)

    errors_dict = {}
    for i, e in enumerate(errors):
        if e: errors_dict[parsers[i].name] = e

    return MarpleResult(
            results,
            links,
            errors_dict,
            warnings,
        )


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
        default=300,
        help='Threshold to discard junk search results',
    )
    parser.add_argument(
        '--results-count',
        action='store',
        type=int,
        default=1000,
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
        choices={'maigret', 'socid_extractor'},
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
        '-d',
        '--debug',
        action='store_true',
        default=False,
        help='Display all the results from sources and debug messages',
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
    if " " in username:
        print(colored('Warning, search by firstname+lastname '
                      'is not fully supported at the moment!\n', 'red'))
        if args.url_filter:
            print(colored('Try to use --no-url-filter option.\n', 'red'))

    result = marple(username, args.results_count, args.url_filter, args.verbose)

    total_collected_count = len(result.all_links)
    uniq_count = len(result.unique_links)

    if args.debug:
        for r in results:
            print(f'{r.url}\n{r.title}\n')

    if args.plugins == 'maigret':
        try:
            import maigret
            db = maigret.MaigretDatabase().load_from_file(maigret.__path__[0]+'/resources/data.json')
            maigret.db = db
        except ImportError:
            print('\tInstall maigret first!')
            print('\tpip3 install maigret')
            exit()

    if args.plugins == 'socid_extractor':
        try:
            import socid_extractor
        except ImportError:
            print('\tInstall maigret first!')
            print('\tpip3 install socid_extractor')
            exit()

    if args.list:
        for r in result.unique_links:
            print(r.url)
        return

    displayed_count = 0

    for r in result.unique_links:
        if r.is_it_likely_username_profile() and r.junk_score <= args.threshold:
            displayed_count += 1

            message = r.url

            if args.verbose:
                message = colored(f'[{r.junk_score}]', 'magenta') + ' ' + message

            if args.plugins == 'maigret' and maigret.db:
                if maigret.db.extract_ids_from_url(r.url):
                    message += colored(' [v] Maigret', 'green')
                else:
                    message += colored(' [ ] Maigret', 'yellow')

            if args.plugins == 'socid_extractor':
                req = requests.get(r.url)
                extract_items = socid_extractor.extract(req.text)
                for k, v in extract_items.items():
                    message += ' \n' + k + ' : ' + v

            print(f'{message}\n{r.title}\n')

    # show status
    status_msg = f'Links: total collected {total_collected_count} / unique with username in URL {uniq_count} / reliable {displayed_count} '

    error_msg = ''
    for p, e in result.errors.items():
        error_msg += f'Problem with source "{p}": {e}\n'

    for w in result.warnings:
        error_msg += f'Warning: {w}\n'

    print(f"{colored(status_msg, 'cyan')}\n{colored(error_msg, 'yellow')}")


if __name__ == '__main__':
    main()
