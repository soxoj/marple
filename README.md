# Marple

<p align="left">
  <p align="left">
    <img src="https://raw.githubusercontent.com/soxoj/marple/main/example.png" height="300"/>
  </p>
</p>


## Summary

Collect links to profiles by username through 10+ search engines ([see the full list below](#supported-sources)).

Features:
- multiple engines
- proxy support
- CSV file export
- plugins
  - pdf metadata extraction
  - social media info [extraction](socid_extractor)

## Quick Start

```
./marple.py soxoj
```

**Results**:
```
https://t.me/soxoj
Contact @soxoj - Telegram

https://github.com/soxoj
soxoj - GitHub

https://coder.social/soxoj
soxoj - Coder Social

https://gitmemory.com/soxoj
soxoj

...

PDF files
https://codeby.net/attachments/v-0-0-1-social-osint-fundamentals-pdf.45770
Social OSINT fundamentals - Codeby.net
/Creator: Google

...

Links: total collected 111 / unique with username in URL 97 / reliable 38 / documents 3
```

Advanced usage:
```
./marple.py soxoj --plugins metadata

./marple.py smirnov --engines google baidu -v
```

## Installation

All you need is Python3. And pip. And requirements, of course.

```
pip3 install -r requirements.txt
```

You need API keys for some search engines (see requirements in [Supported sources](#supported-sources)). Keys should be exported to env in this way:
```
export YANDEX_KEY=key
```

## Options

You can specify 'junk threshold' with option `-t` or `--threshold` (default 300) to get more or less reliable results.

Junk score is summing up from length of link URL and symbols next to username as a part of URL. 

Also you can increase count of results from search engines with option `--results-count` (default 1000). Currently limit is only applicable for Google.

Other options:
```
  -h, --help            show this help message and exit
  -t THRESHOLD, --threshold THRESHOLD
                        Threshold to discard junk search results
  --results-count RESULTS_COUNT
                        Count of results parsed from each search engine
  --no-url-filter       Disable filtering results by usernames in URLs

  --engines {baidu,dogpile,google,bing,ask,aol,torch,yandex,naver,paginated,yahoo,startpage,duckduckgo,qwant}
                        Engines to run (you can choose more than one)

  --plugins {socid_extractor,metadata,maigret} [{socid_extractor,metadata,maigret} ...]
                        Additional plugins to analyze links

  -v, --verbose         Display junk score for each result
  -d, --debug           Display all the results from sources and debug messages
  -l, --list            Display only list of all the URLs
  --proxy PROXY         Proxy string (e.g. https://user:pass@1.2.3.4:8080)
  --csv CSV             Save results to the CSV file
```

## Supported sources

| Name                | Method                                | Requirements      |
| ------------------- | --------------------------------------| ----------------- |
| [Google](http://google.com/)              | scraping                              | None, works out of the box; frequent captcha  |
| [DuckDuckGo](https://duckduckgo.com/)     | scraping                              | None, works out of the box                    |
| [Yandex](https://yandex.ru/)              | XML API                               | [Register and get YANDEX_USER/YANDEX_KEY tokens](https://github.com/fluquid/yandex-search)   |
| [Naver](https://www.naver.com/)           | SerpApi                               | [Register and get SERPAPI_KEY token](https://serpapi.com/)   |
| [Baidu](https://www.baidu.com/)           | SerpApi                               | [Register and get SERPAPI_KEY token](https://serpapi.com/)   |
| [Aol](https://search.aol.com/)            | scraping                              | None, scrapes with pagination  |
| [Ask](https://www.ask.com/)               | scraping                              | None, scrapes with pagination  |
| [Bing](https://www.bing.com/)             | scraping                              | None, scrapes with pagination  |
| [Startpage](https://www.startpage.com/)   | scraping                              | None, scrapes with pagination  |
| [Yahoo](https://yahoo.com/)               | scraping                              | None, scrapes with pagination  |
| [Mojeek](https://www.mojeek.com)          | scraping                              | None, scrapes with pagination  |
| [Dogpile](https://www.dogpile.com/)       | scraping                              | None, scrapes with pagination  |
| [Torch](http://torchdeedp3i2jigzjdmfpn5ttjhthh5wbmda2rr3jvqjg5p77c54dqd.onion)               | scraping                              | Tor proxies (socks5://localhost:9050 by default), scrapes with pagination  |
| [Qwant](https://www.qwant.com/)           | Qwant API                              | Check [if search available](https://www.qwant.com/) in your exit IP country, scrapes with pagination  |


## Development & testing

```sh
$ python3 -m pytest tests
```

## TODO

- [x] Proxy support
- [ ] Engines choose through arguments
- [ ] Exact search filter
- [ ] Engine-specific filters
- [ ] 'Username in title' check

## Mentions and articles

[Sector035 - Week in OSINT #2021-50](https://sector035.nl/articles/2021-50)

[OS2INT - MARPLE: IDENTIFYING AND EXTRACTING SOCIAL MEDIA USER LINKS](https://os2int.com/toolbox/identifying-and-extracting-social-media-user-links-with-marple/)
