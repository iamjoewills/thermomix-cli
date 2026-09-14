"""Cookidoo client factory and shared async runner."""
from __future__ import annotations

import asyncio
import functools
from contextlib import asynccontextmanager

import aiohttp

from cookidoo_api import Cookidoo
from cookidoo_api.helpers import get_localization_options
from cookidoo_api.types import CookidooConfig, CookidooLocalizationConfig

from thermomix_cli.config import ConfigError, Credentials, load_credentials


class CookidooProblem(RuntimeError):
    """Something went wrong talking to Cookidoo, described in plain words."""


async def _resolve_localization(creds: Credentials) -> CookidooLocalizationConfig:
    options = await get_localization_options(country=creds.country, language=creds.language)
    if not options:
        raise CookidooProblem(
            f"Cookidoo has no site for country '{creds.country}' with language "
            f"'{creds.language}'.\nRun `thermomix-cli locale list` to see the "
            "options, then `thermomix-cli setup` to change them."
        )
    return options[0]


@asynccontextmanager
async def cookidoo_session():
    """Yield a logged-in Cookidoo client backed by aiohttp."""
    creds = load_credentials()
    localization = await _resolve_localization(creds)

    async with aiohttp.ClientSession() as session:
        cookidoo = Cookidoo(
            session,
            cfg=CookidooConfig(
                email=creds.email,
                password=creds.password,
                localization=localization,
            ),
        )
        try:
            await cookidoo.login()
        except aiohttp.ClientError as exc:
            raise CookidooProblem(
                "Could not reach Cookidoo. Check your internet connection, then "
                f"try again.\n({exc.__class__.__name__})"
            ) from exc
        except Exception as exc:  # noqa: BLE001 – turned into a plain message below
            raise CookidooProblem(
                "Cookidoo would not accept those details.\n"
                "Check the email address and password by signing in at "
                "https://cookidoo.co.uk, then run `thermomix-cli setup` again.\n"
                f"({exc.__class__.__name__})"
            ) from exc
        yield cookidoo


def asyncio_command(func):
    """Wrap an async typer command body so it runs inside asyncio.run."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper


__all__ = ["ConfigError", "CookidooProblem", "asyncio_command", "cookidoo_session"]
