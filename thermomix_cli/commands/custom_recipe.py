"""Custom recipe (Created Recipes) commands.

Created Recipes are a Cookidoo premium feature. This public build covers the
safe, supported-shaped operations: bring an official recipe into your own
collection, read one back, list them and delete one.
"""
from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from thermomix_cli.client import asyncio_command, cookidoo_session

app = typer.Typer(help="Manage your Created Recipes (a Cookidoo premium feature).")
console = Console()


@app.command("import")
@asyncio_command
async def import_recipe(
    source: str = typer.Argument(
        ...,
        help="Cookidoo recipe ID (e.g. r59322) or the full URL of a recipe to import",
    ),
    serving_size: int = typer.Option(
        None, "--servings", "-s", help="Override serving size (defaults to source recipe)"
    ),
):
    """Copy an existing Cookidoo recipe into your own Created Recipes."""
    async with cookidoo_session() as cookidoo:
        if serving_size is None:
            details = await cookidoo.get_recipe_details(source.split("/")[-1])
            serving_size = details.serving_size
        added = await cookidoo.add_custom_recipe_from(source, serving_size)
        console.print(f"[green]Imported.[/green] Custom recipe ID: [bold]{added.id}[/bold]")


@app.command()
@asyncio_command
async def get(
    recipe_id: str = typer.Argument(..., help="Custom recipe ID"),
    raw: bool = typer.Option(False, "--raw", help="Print full object as JSON"),
    annotations: bool = typer.Option(
        False, "--annotations", help="Print step annotations (timers, temperatures, speeds)"
    ),
):
    """Read one of your created recipes."""
    async with cookidoo_session() as cookidoo:
        recipe = await cookidoo.get_custom_recipe(recipe_id)
        if raw:
            console.print_json(json.dumps(recipe.__dict__, default=lambda o: o.__dict__))
            return

        console.print(f"[bold]{getattr(recipe, 'name', recipe_id)}[/bold]")
        for field in ("id", "total_time", "prep_time", "serving_size", "tools"):
            value = getattr(recipe, field, None)
            if value is not None:
                console.print(f"  {field}: {value}")

        ingredients = getattr(recipe, "ingredients", None) or []
        if ingredients:
            console.print("\n[bold]Ingredients[/bold]")
            for ing in ingredients:
                console.print(f"  - {getattr(ing, 'text', ing)}")

        steps = getattr(recipe, "steps", None) or getattr(recipe, "instructions", None) or []
        if steps:
            console.print("\n[bold]Steps[/bold]")
            for i, step in enumerate(steps, 1):
                text = getattr(step, "text", str(step))
                console.print(f"  {i}. {text}")
                if annotations:
                    anns = getattr(step, "annotations", None) or []
                    for ann in anns:
                        console.print(f"     · {ann}")


@app.command("list")
@asyncio_command
async def list_recipes():
    """List your created recipes."""
    async with cookidoo_session() as cookidoo:
        recipes = await cookidoo.list_custom_recipes()
        if not recipes:
            console.print("[dim]No created recipes yet.[/dim]")
            return
        table = Table()
        table.add_column("id")
        table.add_column("name")
        for recipe in recipes:
            table.add_row(getattr(recipe, "id", "?"), getattr(recipe, "name", "?"))
        console.print(table)


@app.command()
@asyncio_command
async def remove(
    recipe_id: str = typer.Argument(..., help="Custom recipe ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation"),
):
    """Delete one of your created recipes. This cannot be undone."""
    if not yes:
        typer.confirm(f"Delete created recipe {recipe_id}?", abort=True)
    async with cookidoo_session() as cookidoo:
        await cookidoo.remove_custom_recipe(recipe_id)
        console.print(f"[green]Removed[/green] {recipe_id}")
