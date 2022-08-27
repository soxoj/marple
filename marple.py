#!/usr/bin/env python3
import asyncio
import csv
import json
from mock import Mock
import re
import os
from typing import List
from argparse import ArgumentParser as Arguments, RawDescriptionHelpFormatter
import urllib.parse

import aiohttp
import requests
import tqdm
from aiohttp_socks import ProxyConnector
from bs4 import BeautifulSoup as bs
from termcolor import colored

import yandex_search
from PyPDF2 import PdfFileReader
from search_engines import Aol, Ask, Qwant, Bing, Yahoo, Startpage, Dogpile, Mojeek, Torch, Duckduckgo
from serpapi import GoogleSearch as SerpGoogle, BaiduSearch as SerpBaidu

username_marks_symbols = '/.~=?&      -'

junk_regexps = [
    'ref_src=[^&]+',
    'via=[^&]+',
]

junk_end_symbols = '?&/'

links_blacklist = [
    'books.google.ru',
    '/search?q=',
]


class Link:
    url: str
    title: str
    filtered: bool
    source: str

    def __init__(self, url, title, username, source=''):
        self.url = url.lower()
        self.title = title
        self.name = username.lower()
        self.filtered = False
        self.source = source
        self.normalize()

    def __eq__(self, other):
        def normalize(url):
            return url.replace('https://', 'http://')

        return normalize(self.url) == normalize(other.url)

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
        left_symbol, right_symbol = self.username_profile_symbols()
        symbols_score = sum(
            username_marks_symbols.index(i)
            for i in left_symbol + right_symbol
            if i in username_marks_symbols
        )

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
    blacklist_filter = lambda l: all(
        s not in l.url.lower() for s in links_blacklist
    )


    if filter_by_urls:
        for l in links:
            if name.lower() not in l.url.lower():
                l.filtered = True

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


async def create_async_session(proxy=None):
    if proxy:
        connector = ProxyConnector.from_url(proxy)
        return aiohttp.ClientSession(connector=connector)

    return  aiohttp.ClientSession()

class Parser:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:84.0) Gecko/20100101 Firefox/84.0'
    }

    async def request(self, url, proxy=None):
        session = await create_async_session(proxy)
        coro = await session.get(url, headers=self.headers)
        response = await coro.text()
        await session.close()

        return response

    async def run(self, storage, username, count=100, lang='en', proxy=None):
        url = self.make_url(username, count, lang)
        try:
            html = await self.request(url)
            results = await self.parse(html, username)
        except Exception as e:
            return (self.name, f'Error of type "{type(e)}": {e}')

        if not results:
            return self.name, 'Got no results'

        storage += results


class YandexParser:
    name = 'Yandex API search'

    """
        You should have env variables with user and key, e.g.

        export YANDEX_USER=user
        export YANDEX_KEY=key
    """
    async def run(self, storage, username, count=100, lang='en', proxy=None):
        try:
            yandex = yandex_search.Yandex()
            results = yandex.search(username).items
        except KeyError as e:
            return (self.name, f'Not found env variable {str(e)}')
        except Exception as e:
            return (self.name, str(e))

        tuples_list = [Link(r["url"], r["title"], username, source='Yandex') for r in results]

        storage += tuples_list


class GoogleParser(Parser):
    name = 'Google scraping'

    def __init__(self, quoted=True):
        self.quoted = quoted
        super().__init__()

    def make_url(self, username, count, lang):
        processed_username = f'"{username}"' if self.quoted else username
        return f'https://www.google.com/search?q={processed_username}&num={count}&hl={lang}'

    async def parse(self, html, username):
        results = []

        soup = bs(html, 'html.parser')
        result_block = soup.find_all('div', attrs={'class': 'g'})

        for result in result_block:
            link = result.find('a', href=True)
            title = result.find('h3')

            if link and title:
                results.append(Link(link['href'], title.text, username, source='Google'))

        return results


# old unused parser
class DuckParserOld(Parser):
    name = 'DuckDuckGo scraping'

    def make_url(self, username, count, lang):
        return f'https://duckduckgo.com/html/?q={username}'

    async def parse(self, html, username):
        results = []

        soup = bs(html, 'html.parser')
        result_block = soup.find_all('a', class_='result__a', href=True)

        for result in result_block:
            link = result['href']
            title = result.text

            if link and title:
                results.append(Link(link, title, username, source='DuckDuckGo'))

        return results


class PaginatedParser:
    name = 'Engine for scraping with pagination'

    def __init__(self, base_class=None):
        if base_class:
            self.base_class = base_class

    async def run(self, storage, username, count=100, lang='en', proxy=None):
        err = None
        results = []
        kwargs = {}

        if proxy:
            kwargs['proxy'] = proxy

        try:
            engine = self.base_class(print_func=Mock, **kwargs)
            results = await engine.search(username)
            rows = results.results()
        except Exception as e:
            err = (self.name, e)
        finally:
            try:
                await engine.close()
            except:
                pass

        new_results = [
            Link(r["link"], r["title"], username, source=self.name.split()[0])
            for r in results
            if 'link' in r and 'title' in r
        ]

        storage += new_results
        if not new_results:
            err = (self.name, 'Got no results')

        return err


class QwantParser(PaginatedParser):
    name = 'Qwant scraping with pagination'
    base_class = Qwant

    async def run(self, storage, username, count=100, lang='en', proxy=None):
        check_url = 'https://www.qwant.com/'
        session = await create_async_session(proxy)
        coro = await session.get(check_url)
        response = await coro.text()
        await session.close()

        if 'Unfortunately we are not yet available in your country.' in response:
            return ('Qwant', 'fake results, engine is not available in exit IP country')

        super().run(self, storage, username, count, lang, proxy)

class AolParser(PaginatedParser):
    name = 'Aol scraping with pagination'
    base_class = Aol


class AskParser(PaginatedParser):
    name = 'Ask scraping with pagination'
    base_class = Ask


class BingParser(PaginatedParser):
    name = 'Bing scraping with pagination'
    base_class = Bing


class YahooParser(PaginatedParser):
    name = 'Yahoo scraping with pagination'
    base_class = Yahoo


class StartpageParser(PaginatedParser):
    name = 'Startpage scraping with pagination'
    base_class = Startpage


class DogpileParser(PaginatedParser):
    name = 'Dogpile scraping with pagination'
    base_class = Dogpile


class TorchParser(PaginatedParser):
    name = 'Torch scraping with pagination'
    base_class = Torch


class DuckduckgoParser(PaginatedParser):
    name = 'Duckduckgo scraping with pagination'
    base_class = Duckduckgo


# TODO: pagination
class NaverParser:
    name = 'Naver parser (SerpApi)'

    """
        You should have env variables with key, e.g.

        export SERPAPI_KEY=key
    """
    async def run(self, storage, username, count=100, lang='en', proxy=None):
        params = {
          "engine": "naver",
          "query": username,
          "where": "web",
          "api_key": os.getenv('SERPAPI_KEY')
        }

        try:
            search = SerpGoogle(params)
            results = search.get_dict()
            organic_results = results.get('organic_results', [])
        except KeyError as e:
            return (self.name, f'Not found env variable {str(e)}')
        except Exception as e:
            return (self.name, str(e))

        tuples_list = [Link(r["link"], r["title"], username, source='Naver') for r in organic_results]

        storage += tuples_list


# TODO: pagination
class BaiduParser:
    name = 'Baidu parser (SerpApi)'

    """
        You should have env variables with key, e.g.

        export SERPAPI_KEY=key
    """
    async def run(self, storage, username, count=100, lang='en', proxy=None):
        params = {
          "engine": "baidu",
          "q": username,
          "api_key": os.getenv('SERPAPI_KEY')
        }

        try:
            search = SerpBaidu(params)
            results = search.get_dict()
            organic_results = results['organic_results']
        except KeyError as e:
            return (self.name, f'Not found env variable {str(e)}')
        except Exception as e:
            return (self.name, str(e))

        session = await create_async_session(proxy)

        async def baidu_resolve(res):
            resp = await session.request('GET', res['link'], allow_redirects=False)
            location = resp.headers.get('location')
            res['link'] = location

        coros = [baidu_resolve(r) for r in organic_results]
        await asyncio.gather(*coros)
        await session.close()

        tuples_list = [Link(r["link"], r["title"], username, source='Naver') for r in organic_results]

        storage += tuples_list


class MarpleResult:
    def __init__(self, results, links, errors, warnings):
        self.all_links = results
        self.unique_links = links
        self.errors = errors
        self.warnings = warnings


async def marple(username, max_count, url_filter_enabled, is_debug=False, proxy=None,
                 custom_engines=None):
    parsers = [
        GoogleParser(),
        YandexParser(),
        AolParser(),
        QwantParser(),
        YahooParser(),
        StartpageParser(),
        AskParser(),
        BingParser(),
        DogpileParser(),
        TorchParser(),
        DuckduckgoParser(),
        NaverParser(),
        BaiduParser(),
    ]

    if custom_engines:
        parsers = [globals()[f'{e.capitalize()}Parser']() for e in custom_engines]

    results = []
    errors = []
    warnings = []

    debug_filename = f'debug_{username}.json'

    if not is_debug or not os.path.exists(debug_filename):
        coros = [parser.run(results, username, max_count, proxy=proxy) for parser in parsers]

        errors = [await f for f in tqdm.tqdm(asyncio.as_completed(coros), total=len(coros))]

        if is_debug:
            with open(debug_filename, 'w') as results_file:
                json.dump({'res': results}, results_file, cls=LinkEncoder, indent=4)
    else:
        with open(debug_filename) as results_file:
            results = [Link(l['url'], l['title'], username, l['source']) for l in json.load(results_file)['res']]

        warnings.append(colored(f'Links were loaded from file {debug_filename}!', 'yellow'))

    links = merge_links(results, username, url_filter_enabled)
    links = sorted(links, key=lambda x: x.junk_score)

    return MarpleResult(
            results,
            links,
            errors,
            warnings,
        )


def get_engines_names():
    return {
        k.split('Parser')[0].lower()
        for k in globals()
        if k.lower().endswith('parser') and k != 'Parser'
    }


def main():
    parser = Arguments(
        formatter_class=RawDescriptionHelpFormatter,
        description='Marple v0.0.1\n'
        'Collect links to profiles by username through search engines',
    )
    parser.add_argument(
        'name',
        help='Target username or first/lastname to search by.',
    )
    parser.add_argument(
        '--username',
        help='Target username',
    )
    parser.add_argument(
        '--firstname',
        help='Target firstname, e.g. Jon',
    )
    parser.add_argument(
        '--lastname',
        help='Target lastname/surname, e.g. Snow',
    )
    parser.add_argument(
        '--middlename',
        help='Target middlename/patronymic/avonymic/matronymic, e.g. Snow',
    )
    parser.add_argument(
        '--birthdate',
        help='Target date of birth an any format, e.g. 02/17/2009',
    )
    parser.add_argument(
        '--country',
        help='Target country any format, e.g. UK',
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
        '--engines',
        dest='engines',
        nargs='+',
        choices=get_engines_names(),
        help='Engines to run (you can choose more than one)',
    )

    parser.add_argument(
        '--plugins',
        dest='plugins',
        nargs='+',
        default='',
        choices={'maigret', 'socid_extractor', 'metadata'},
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
    parser.add_argument(
        '--proxy',
        type=str,
        default="",
        help="Proxy string (e.g. https://user:pass@1.2.3.4:8080)",
    )
    parser.add_argument(
        '--csv',
        type=str,
        default="",
        help="Save results to the CSV file",
    )
    args = parser.parse_args()

    username = args.name
    if " " in username:
        print(colored('Warning, search by firstname+lastname '
                      'is not fully supported at the moment!\n', 'red'))
        if args.url_filter:
            print(colored('Try to use --no-url-filter option.\n', 'red'))

    loop = asyncio.get_event_loop()

    result = loop.run_until_complete(marple(username, args.results_count, args.url_filter,
                                            is_debug=args.debug, proxy=args.proxy,
                                            custom_engines=args.engines))

    total_collected_count = len(result.all_links)
    uniq_count = len(result.unique_links)

    if args.debug:
        for r in result.all_links:
            print(f'{r.url}\n{r.title}\n')

    if 'maigret' in args.plugins:
        try:
            import maigret
            db = maigret.MaigretDatabase().load_from_file(
                f'{maigret.__path__[0]}/resources/data.json'
            )

            maigret.db = db
        except ImportError:
            print('\tInstall maigret first!')
            print('\tpip3 install maigret')
            exit()

    if 'socid_extractor' in args.plugins:
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

    def is_likely_profile(r):
        return r.is_it_likely_username_profile() and r.junk_score <= args.threshold and not r.filtered

    # reliable links section
    for r in result.unique_links:
        if is_likely_profile(r):
            displayed_count += 1

            message = r.url

            if args.verbose:
                message = colored(f'[{r.junk_score}]', 'magenta') + ' ' + \
                          colored(f'[{r.source}]', 'green') + ' ' + message

            if 'maigret' in args.plugins and maigret.db:
                if maigret.db.extract_ids_from_url(r.url):
                    message += colored(' [v] Maigret', 'green')
                else:
                    message += colored(' [ ] Maigret', 'yellow')

            if 'socid_extractor' in args.plugins:
                try:
                    req = requests.get(r.url)
                    extract_items = socid_extractor.extract(req.text)
                    for k, v in extract_items.items():
                        message += ' \n' + k + ' : ' + v
                except Exception as e:
                    print(colored(e, 'red'))

            print(f'{message}\n{r.title}\n')

    pdf_count = 0

    def is_pdf_file(url):
        return url.endswith('pdf') or '-pdf.' in url

    # pdf links section
    for r in result.unique_links:
        if is_pdf_file(r.url):
            if pdf_count == 0:
                print(colored('PDF files (without junk filtering)', 'cyan'))

            pdf_count += 1

            message = r.url

            if args.verbose:
                message = colored(f'[{r.junk_score}]', 'magenta') + ' ' + \
                          colored(f'[{r.source}]', 'green') + ' ' + message

            print(f'{message}\n{r.title}')

            if 'metadata' in args.plugins:
                filename = r.url.split('/')[-1]
                if not os.path.exists(username):
                    os.mkdir(username)
                else:
                    try:
                        if not os.path.exists(os.path.join(username, filename)):
                            print(colored(f'Downloading {r.url} to file {filename} ...', 'cyan'))
                            req = requests.get(r.url)
                            with open(os.path.join(username, filename), 'wb') as f:
                                f.write(req.content)

                        with open(os.path.join(username, filename), 'rb') as f:
                            pdf = PdfFileReader(f)
                            info = pdf.getDocumentInfo()
                            for k,v in info.items():
                                print(colored(f'{k}: {v}', 'yellow'))

                    except Exception as e:
                        print(colored(e, 'red'))

            print()

    # show status
    status_msg = f'Links: total collected {total_collected_count} / unique with username in URL {uniq_count} / reliable {displayed_count} / documents {pdf_count}'

    error_msg = ''
    for r in result.errors:
        error_msg += f'Problem with source "{r[0]}": {r[1]}\n' if r else ''

    for w in result.warnings:
        error_msg += f'Warning: {w}\n'

    print(f"{colored(status_msg, 'cyan')}\n{colored(error_msg, 'yellow')}")

    if args.csv:
        with open(args.csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
            writer.writerow(['URL', 'Title', 'Score', 'Is profile page', 'Is PDF'])

            def write_links(condition):
                for r in result.unique_links:
                    if not condition(r):
                        continue
                    writer.writerow([r.url, r.title, r.junk_score, is_likely_profile(r), is_pdf_file(r.url)])

            write_links(lambda x: is_likely_profile(x))
            write_links(lambda x: not is_likely_profile(x))

        print(colored(f'Results was saved to CSV file {args.csv}', 'red'))

if __name__ == '__main__':
    main()
