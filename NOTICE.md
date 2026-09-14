# Credits

Thermomix CLI is a thin command-line layer over other people's work. The
interesting parts of talking to Cookidoo were solved upstream.

## The library this is built on

- **[cookidoo-api](https://github.com/miaucl/cookidoo-api)** by miaucl – the
  Python client that works out how to sign in to Cookidoo and how its endpoints
  behave. Every account, recipe, collection, calendar and shopping-list call in
  this tool goes through it. Without it there would be nothing here.

## Runtime dependencies

Installed automatically, each under its own licence:

- **[Typer](https://github.com/fastapi/typer)** – the command-line interface
- **[Rich](https://github.com/Textualize/rich)** – the tables and colour
- **[aiohttp](https://github.com/aio-libs/aiohttp)** – the HTTP session

## Installer

- **[uv](https://github.com/astral-sh/uv)** by Astral – downloaded by
  `install.sh` at a pinned version, verified against the SHA-256 published with
  that release, and used to fetch a private copy of CPython. It is installed
  inside this tool's own folder and removed by `uninstall.sh`. An existing `uv`
  on the machine is not touched.
- **[python-build-standalone](https://github.com/astral-sh/python-build-standalone)**
  – the CPython build uv downloads.

## Prior art

Joe Wills was not the first to automate Cookidoo, and this tool does not claim
to be. Cookiput, `cookidoo-api` itself, `tmx-cli` and several MCP servers came
earlier and solved parts of the same problem.

## Trademarks

Thermomix® and Cookidoo® are trademarks of Vorwerk. This project is not
affiliated with, supported by or endorsed by Vorwerk, and its use of those names
is descriptive only.

## Licence

You may install and run this tool for personal use. All other rights are
reserved. Third-party dependencies retain their own licences — everything
listed above keeps the terms its own authors set.
