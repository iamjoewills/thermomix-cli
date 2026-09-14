"""Shopping list commands."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from cookidoo_api.types import CookidooAdditionalItem, CookidooIngredientItem

from thermomix_cli.client import asyncio_command, cookidoo_session

app = typer.Typer(help="Shopping list – per-recipe ingredients and ad-hoc items.")
console = Console()


@app.command("recipes")
@asyncio_command
async def recipes_in_list():
    """Show recipes whose ingredients are currently on the shopping list."""
    async with cookidoo_session() as cookidoo:
        recipes = await cookidoo.get_shopping_list_recipes()
        if not recipes:
            console.print("[dim]No recipes on the shopping list.[/dim]")
            return
        table = Table()
        table.add_column("id")
        table.add_column("name")
        table.add_column("source")
        for r in recipes:
            table.add_row(
                getattr(r, "id", "?"),
                getattr(r, "name", "?"),
                "custom" if getattr(r, "is_customer_recipe", False) else "official",
            )
        console.print(table)


@app.command("ingredients")
@asyncio_command
async def ingredients():
    """Show all ingredient items on the shopping list."""
    async with cookidoo_session() as cookidoo:
        items = await cookidoo.get_ingredient_items()
        if not items:
            console.print("[dim]Empty shopping list.[/dim]")
            return
        table = Table()
        table.add_column("id")
        table.add_column("name")
        table.add_column("qty")
        table.add_column("got it?")
        for item in items:
            table.add_row(
                getattr(item, "id", "?"),
                getattr(item, "name", "?"),
                str(getattr(item, "notation", "")),
                "✓" if getattr(item, "is_owned", False) else " ",
            )
        console.print(table)


@app.command("additional")
@asyncio_command
async def additional():
    """Show additional (non-recipe) items on the shopping list."""
    async with cookidoo_session() as cookidoo:
        items = await cookidoo.get_additional_items()
        if not items:
            console.print("[dim]No additional items.[/dim]")
            return
        table = Table()
        table.add_column("id")
        table.add_column("name")
        table.add_column("got it?")
        for item in items:
            table.add_row(
                getattr(item, "id", "?"),
                getattr(item, "name", "?"),
                "✓" if getattr(item, "is_owned", False) else " ",
            )
        console.print(table)


@app.command("add-recipe")
@asyncio_command
async def add_recipe(
    recipe_id: str = typer.Argument(...),
    custom: bool = typer.Option(False, "--custom", help="Treat as a custom recipe"),
):
    """Add a recipe's ingredients to the shopping list."""
    async with cookidoo_session() as cookidoo:
        if custom:
            items = await cookidoo.add_ingredient_items_for_custom_recipes([recipe_id])
        else:
            items = await cookidoo.add_ingredient_items_for_recipes([recipe_id])
        console.print(f"[green]Added[/green] {len(items)} ingredients from {recipe_id}")


@app.command("remove-recipe")
@asyncio_command
async def remove_recipe(
    recipe_id: str = typer.Argument(...),
    custom: bool = typer.Option(False, "--custom"),
):
    """Remove a recipe's ingredients from the shopping list."""
    async with cookidoo_session() as cookidoo:
        if custom:
            await cookidoo.remove_ingredient_items_for_custom_recipes([recipe_id])
        else:
            await cookidoo.remove_ingredient_items_for_recipes([recipe_id])
        console.print(f"[green]Removed[/green] ingredients for {recipe_id}")


@app.command("add-item")
@asyncio_command
async def add_item(items: list[str] = typer.Argument(..., help="One or more item names")):
    """Add ad-hoc shopping items (e.g. tm shopping add-item Salt Butter)."""
    async with cookidoo_session() as cookidoo:
        added = await cookidoo.add_additional_items(items)
        for item in added:
            console.print(f"[green]+[/green] {item.name} (id: {item.id})")


@app.command("check")
@asyncio_command
async def check(
    item_id: str = typer.Argument(..., help="Ingredient item ID"),
    additional: bool = typer.Option(False, "--additional", help="The id is for an additional item, not an ingredient"),
):
    """Toggle the 'already got it' flag on an item."""
    async with cookidoo_session() as cookidoo:
        if additional:
            current = await cookidoo.get_additional_items()
            target = next((it for it in current if it.id == item_id), None)
            if not target:
                console.print(f"[red]No additional item with id {item_id}[/red]")
                raise typer.Exit(1)
            target_dict = target.__dict__.copy()
            target_dict["is_owned"] = not target.is_owned
            await cookidoo.edit_additional_items_ownership([CookidooAdditionalItem(**target_dict)])
        else:
            current = await cookidoo.get_ingredient_items()
            target = next((it for it in current if it.id == item_id), None)
            if not target:
                console.print(f"[red]No ingredient item with id {item_id}[/red]")
                raise typer.Exit(1)
            target_dict = target.__dict__.copy()
            target_dict["is_owned"] = not target.is_owned
            await cookidoo.edit_ingredient_items_ownership([CookidooIngredientItem(**target_dict)])
        console.print(f"[green]Toggled[/green] {item_id}")


@app.command("remove-item")
@asyncio_command
async def remove_item(item_id: str = typer.Argument(...)):
    """Remove an additional item from the shopping list."""
    async with cookidoo_session() as cookidoo:
        await cookidoo.remove_additional_items([item_id])
        console.print(f"[green]Removed[/green] {item_id}")


@app.command()
@asyncio_command
async def clear():
    """Clear the entire shopping list."""
    confirm = typer.confirm("Clear the entire shopping list?")
    if not confirm:
        raise typer.Abort()
    async with cookidoo_session() as cookidoo:
        await cookidoo.clear_shopping_list()
        console.print("[green]Shopping list cleared.[/green]")
