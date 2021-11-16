# Marple

## Summary

Collect links to profiles by username through search engines (currently Google and DuckDuckGo).

## Quick Start

```
./marple.py soxoj
```

**Results**:
```
[18] https://t.me/soxoj
Contact @soxoj - Telegram

[24] https://github.com/soxoj
soxoj - GitHub

[26] https://coder.social/soxoj
soxoj - Coder Social

[27] https://gitmemory.com/soxoj
soxoj

[27] https://pypi.org/user/soxoj
Profile of soxoj · PyPI

...
```

## Installation

```
pip3 install -r requirements.txt
```

## Options

You can specify 'junk threshold' with option `-t` or `--threshold` (default 100) to filter less or more junk results.

Junk score is summing up from length of link URL and symbols next to username as a part of URL. 

Also you can increase count of results from search engines with option `--results-count` (default 100). Currently limit is onle applicable for Google.

## TODO

- [ ] Proxy support
- [ ] Additional search engines
- [ ] Engine-specific filters
