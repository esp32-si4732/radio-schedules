# Radio Schedules

Convert EiBi, Aoki, and HFCC radio schedules into a consistent, validated CSV format for receiver applications, supporting both local use and automated CI exports.

## Documentation

- [Use cases](docs/use-cases.md)
- [Design](docs/design.md)
- [CSV format](docs/format.md)

## Getting started

Install [uv](https://github.com/astral-sh/uv#installation), then run the tool directly from GitHub using Python 3.14:

```sh
uv tool run --python 3.14 \
  --from git+https://github.com/esp32-si4732/radio-schedules.git@main \
  rsked --help
```

## Development checks

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Data sources

EiBi

- Season discovery page: http://eibispace.de/
- Downloaded schedule: `http://eibispace.de/dx/sked-{season}.csv`, with a lowercase season, for example http://eibispace.de/dx/sked-a26.csv
- Format and lookup tables: http://eibispace.de/dx/README.TXT
- Alternative latest CSV: http://eibispace.de/dx/sked-latest.csv (not used by the downloader; local copies require the matching `--season`).

Aoki

- Download page: https://www1.s2.starcat.ne.jp/ndxc/nnk.htm
- Archive URLs are discovered from that page, not constructed from the season. A26 example: https://www1.m2.mediacat.ne.jp/binews/ut/xt/xta26.zip
- The adapter reads the XLSX member (`xta26.xlsx` in the A26 archive), not the accompanying text exports.
- The archive's spreadsheet includes the marker legend and TIB/TKS definitions; other country names use the bundled ITU table.

HFCC

- Season discovery page: https://new.hfcc.org/data/
- Archive URLs are discovered from that page.
- A26 example: https://new.hfcc.org/data/a26/a26allx2.zip
- B26 example: https://new.hfcc.org/data/b26/b26allx2.zip
- Archives include admin.txt, language.txt, site.txt, antenna.txt, broadcas.txt, and fmorg.txt.
- [ITU HFBC fixed-width format and field definitions](https://www.itu.int/en/ITU-R/terrestrial/broadcast/HFBC/Documents/File%20format-2022-E.pdf)
- [HFCC schedule field explanations](https://new.hfcc.org/drm/help.html)

ITU geographical codes and names (bundled snapshot, not downloaded during conversion)

- https://www.itu.int/gladapp/GeographicalArea/List
