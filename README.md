# Marple

## Summary

Collect links to profiles by username through search engines (see the full list below).

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

https://pypi.org/user/soxoj
Profile of soxoj · PyPI

...
Links: total collected 1000 / unique with username in URL 100 / reliable 90
```

## Installation

```
pip3 install -r requirements.txt
```

## Options

You can specify 'junk threshold' with option `-t` or `--threshold` (default 300) to get more or less reliable results.

Junk score is summing up from length of link URL and symbols next to username as a part of URL. 

Also you can increase count of results from search engines with option `--results-count` (default 1000). Currently limit is onle applicable for Google.

Other options:
```
  --no-url-filter       Disable filtering results by usernames in URLs

  --plugin {socid_extractor,maigret}
                        Additional plugins to analyze links

  -v, --verbose         Display junk score for each result
  -l, --list            Display only list of all the URLs
```

## Supported sources

| Name                | Method                                | Requirements      |
| ------------------- | --------------------------------------| ----------------- |
| Google              | scraping                              | None, works out of the box; frequent captcha  |
| DuckDuckGo          | scraping                              | None, works out of the box                    |
| Yandex              | XML API                               | [Register and get USER/API tokens](https://github.com/fluquid/yandex-search)   |

## TODO

- [ ] Proxy support
- [ ] Additional search engines
- [ ] Engine-specific filters
