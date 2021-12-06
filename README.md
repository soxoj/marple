# Marple

## Summary

Collect links to profiles by username through search engines (see the full list below).

Features:
- multiple engines
- proxy support
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

## Installation

All you need is Python3. And pip. And requirements, of course.

```
pip3 install -r requirements.txt
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
  --plugin {socid_extractor,metadata,maigret}
                        Additional plugins to analyze links
  -v, --verbose         Display junk score for each result
  -d, --debug           Display all the results from sources and debug messages
  -l, --list            Display only list of all the URLs
  --proxy PROXY         Proxy string (e.g. https://user:pass@1.2.3.4:8080)
```

## Supported sources

| Name                | Method                                | Requirements      |
| ------------------- | --------------------------------------| ----------------- |
| Google              | scraping                              | None, works out of the box; frequent captcha  |
| DuckDuckGo          | scraping                              | None, works out of the box                    |
| Yandex              | XML API                               | [Register and get USER/API tokens](https://github.com/fluquid/yandex-search)   |

## Development & testing

```sh
$ python3 -m pytest tests
```

## TODO

- [v] Proxy support
- [ ] Additional search engines
- [ ] Engine-specific filters
