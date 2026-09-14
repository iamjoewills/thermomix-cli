"""Official Cookidoo recipe lookups."""
from __future__ import annotations

import json

import typer
from rich.console import Console

from thermomix_cli.client import asyncio_command, cookidoo_session

app = typer.Typer(help="Inspect official Cookidoo recipes by ID.")
console = Console()


@app.command()
@asyncio_command
async def get(
    recipe_id: str = typer.Argument(..., help="Cookidoo recipe ID, e.g. r59322"),
    raw: bool = typer.Option(False, "--raw", help="Print the full object as JSON"),
):
    """Get an official Cookidoo recipe's shopping-relevant details."""
    async with cookidoo_session() as cookidoo:
        details = await cookidoo.get_recipe_details(recipe_id)
        if raw:
            console.print_json(json.dumps(details.__dict__, default=str))
            return
        console.print(f"[bold]{getattr(details, 'name', recipe_id)}[/bold]")
        for field in ("serving_size", "total_time", "prep_time", "active_time"):
            value = getattr(details, field, None)
            if value is not None:
                console.print(f"  {field}: {value}")
        ingredients = getattr(details, "ingredients", None) or []
        if ingredients:
            console.print("\n[bold]Ingredients[/bold]")
            for ing in ingredients:
                name = getattr(ing, "name", str(ing))
                qty = getattr(ing, "quantity", None)
                console.print(f"  - {qty + ' ' if qty else ''}{name}")
