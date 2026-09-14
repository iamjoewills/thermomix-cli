"""Locale discovery."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from cookidoo_api.helpers import (
    get_country_options,
    get_language_options,
    get_localization_options,
)
from thermomix_cli.client import asyncio_command

app = typer.Typer(help="Discover Cookidoo country / language options.")
console = Console()


@app.command()
@asyncio_command
async def countries():
    """List all supported country codes."""
    codes = await get_country_options()
    console.print(", ".join(sorted(codes)))


@app.command()
@asyncio_command
async def languages():
    """List all supported languages."""
    langs = await get_language_options()
    console.print(", ".join(sorted(langs)))


@app.command("list")
@asyncio_command
async def list_localizations(
    country: str = typer.Option(None, help="Filter by country code (e.g. gb)"),
    language: str = typer.Option(None, help="Filter by language (e.g. en-GB)"),
):
    """List localizations matching the filter."""
    options = await get_localization_options(country=country, language=language)
    if not options:
        console.print("[yellow]No matches.[/yellow]")
        return
    table = Table()
    table.add_column("country")
    table.add_column("language")
    table.add_column("url")
    for opt in options:
        table.add_row(opt.country_code, opt.language, opt.url)
    console.print(table)
