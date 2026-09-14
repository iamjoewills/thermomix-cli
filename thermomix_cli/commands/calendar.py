"""My Week / calendar planning commands."""
from __future__ import annotations

from datetime import date, datetime

import typer
from rich.console import Console
from rich.table import Table

from thermomix_cli.client import asyncio_command, cookidoo_session

app = typer.Typer(help="My Week / day planner – schedule recipes for a date.")
console = Console()


def _parse_date(value: str | None) -> date:
    if not value:
        return date.today()
    return datetime.strptime(value, "%Y-%m-%d").date()


@app.command()
@asyncio_command
async def week(
    on: str = typer.Option(None, "--on", help="Any date in the desired week (YYYY-MM-DD). Defaults to today"),
):
    """Show recipes planned for the week containing the given date."""
    async with cookidoo_session() as cookidoo:
        target = _parse_date(on)
        week_data = await cookidoo.get_recipes_in_calendar_week(target)
        if not week_data:
            console.print("[dim]Nothing planned this week.[/dim]")
            return
        table = Table()
        table.add_column("day")
        table.add_column("recipes")
        for day in week_data:
            day_key = getattr(day, "day_key", "?")
            recipes = (
                getattr(day, "recipe_ids", None)
                or getattr(day, "customer_recipe_ids", None)
                or []
            )
            table.add_row(str(day_key), ", ".join(recipes) if recipes else "-")
        console.print(table)


@app.command()
@asyncio_command
async def add(
    recipe_id: str = typer.Argument(..., help="Official recipe ID, e.g. r59322"),
    on: str = typer.Option(None, "--on", help="Day to plan it on (YYYY-MM-DD). Defaults to today"),
):
    """Add an OFFICIAL Cookidoo recipe to the day plan."""
    async with cookidoo_session() as cookidoo:
        target = _parse_date(on)
        await cookidoo.add_recipes_to_calendar(target, [recipe_id])
        console.print(f"[green]Planned[/green] {recipe_id} for {target}")


@app.command("add-custom")
@asyncio_command
async def add_custom(
    recipe_id: str = typer.Argument(..., help="Custom recipe ID"),
    on: str = typer.Option(None, "--on", help="Day to plan it on (YYYY-MM-DD). Defaults to today"),
):
    """Add a CUSTOM (created) recipe to the day plan."""
    async with cookidoo_session() as cookidoo:
        target = _parse_date(on)
        await cookidoo.add_custom_recipes_to_calendar(target, [recipe_id])
        console.print(f"[green]Planned[/green] custom {recipe_id} for {target}")


@app.command()
@asyncio_command
async def remove(
    recipe_id: str = typer.Argument(...),
    on: str = typer.Option(None, "--on"),
):
    """Remove an official recipe from the day plan."""
    async with cookidoo_session() as cookidoo:
        target = _parse_date(on)
        await cookidoo.remove_recipe_from_calendar(target, recipe_id)
        console.print(f"[green]Removed[/green] {recipe_id} from {target}")


@app.command("remove-custom")
@asyncio_command
async def remove_custom(
    recipe_id: str = typer.Argument(...),
    on: str = typer.Option(None, "--on"),
):
    """Remove a custom recipe from the day plan."""
    async with cookidoo_session() as cookidoo:
        target = _parse_date(on)
        await cookidoo.remove_custom_recipe_from_calendar(target, recipe_id)
        console.print(f"[green]Removed[/green] custom {recipe_id} from {target}")
