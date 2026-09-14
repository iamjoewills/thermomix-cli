"""Collection commands – managed (saved official) and custom (your own)."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from thermomix_cli.client import asyncio_command, cookidoo_session

app = typer.Typer(help="Saved Cookidoo collections and your own custom collections.")
managed = typer.Typer(help="Saved official Cookidoo collections.")
custom = typer.Typer(help="Your own custom collections.")
app.add_typer(managed, name="managed")
app.add_typer(custom, name="custom")

console = Console()


def _collection_table(collections):
    table = Table()
    table.add_column("id")
    table.add_column("name")
    table.add_column("recipes")
    for col in collections:
        recipes = getattr(col, "recipes", None) or getattr(col, "recipe_ids", None) or []
        table.add_row(
            getattr(col, "id", "?"),
            getattr(col, "name", "?") or getattr(col, "title", "?"),
            str(len(recipes)) if recipes else "-",
        )
    return table


@managed.command("list")
@asyncio_command
async def managed_list(
    page: int = typer.Option(0, "--page", help="Page number (paginated)"),
):
    """List saved official collections."""
    async with cookidoo_session() as cookidoo:
        cols = await cookidoo.get_managed_collections(page=page)
        console.print(_collection_table(cols))


@managed.command("count")
@asyncio_command
async def managed_count():
    """Count of saved official collections."""
    async with cookidoo_session() as cookidoo:
        count, total_pages = await cookidoo.count_managed_collections()
        console.print(f"{count} collections across {total_pages} page(s)")


@managed.command("add")
@asyncio_command
async def managed_add(collection_id: str = typer.Argument(..., help="Collection ID, e.g. col500401")):
    """Save an official collection to your library."""
    async with cookidoo_session() as cookidoo:
        await cookidoo.add_managed_collection(collection_id)
        console.print(f"[green]Saved[/green] {collection_id}")


@managed.command("remove")
@asyncio_command
async def managed_remove(collection_id: str = typer.Argument(...)):
    """Unsave an official collection."""
    async with cookidoo_session() as cookidoo:
        await cookidoo.remove_managed_collection(collection_id)
        console.print(f"[green]Unsaved[/green] {collection_id}")


@custom.command("list")
@asyncio_command
async def custom_list(page: int = typer.Option(0, "--page")):
    """List your custom collections."""
    async with cookidoo_session() as cookidoo:
        cols = await cookidoo.get_custom_collections(page=page)
        console.print(_collection_table(cols))


@custom.command("count")
@asyncio_command
async def custom_count():
    """Count of your custom collections."""
    async with cookidoo_session() as cookidoo:
        count, total_pages = await cookidoo.count_custom_collections()
        console.print(f"{count} collections across {total_pages} page(s)")


@custom.command("create")
@asyncio_command
async def custom_create(name: str = typer.Argument(..., help="Name for the new collection")):
    """Create a new custom collection."""
    async with cookidoo_session() as cookidoo:
        col = await cookidoo.add_custom_collection(name)
        console.print(f"[green]Created[/green] {col.id}: {name}")


@custom.command("remove")
@asyncio_command
async def custom_remove(collection_id: str = typer.Argument(...)):
    """Delete a custom collection."""
    async with cookidoo_session() as cookidoo:
        await cookidoo.remove_custom_collection(collection_id)
        console.print(f"[green]Removed[/green] {collection_id}")


@custom.command("add-recipe")
@asyncio_command
async def custom_add_recipe(
    collection_id: str = typer.Argument(...),
    recipe_id: str = typer.Argument(...),
):
    """Add a recipe to a custom collection."""
    async with cookidoo_session() as cookidoo:
        await cookidoo.add_recipes_to_custom_collection(collection_id, [recipe_id])
        console.print(f"[green]Added[/green] {recipe_id} to {collection_id}")


@custom.command("remove-recipe")
@asyncio_command
async def custom_remove_recipe(
    collection_id: str = typer.Argument(...),
    recipe_id: str = typer.Argument(...),
):
    """Remove a recipe from a custom collection."""
    async with cookidoo_session() as cookidoo:
        await cookidoo.remove_recipe_from_custom_collection(collection_id, recipe_id)
        console.print(f"[green]Removed[/green] {recipe_id} from {collection_id}")
