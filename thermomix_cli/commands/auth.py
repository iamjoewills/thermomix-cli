"""Auth and account info commands.

These three are read-only: they sign in and report back. Nothing on your
Cookidoo account is created, changed or deleted by any of them.
"""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from thermomix_cli.client import asyncio_command, cookidoo_session

app = typer.Typer(help="Sign in, check who you are, check your subscription.")
console = Console()


@app.command()
@asyncio_command
async def login():
    """Check your saved details work by signing in once."""
    async with cookidoo_session() as _:
        console.print("[green]Signed in.[/green] Your details work.")
        console.print("Next, try: [bold]thermomix-cli auth whoami[/bold]")


@app.command()
@asyncio_command
async def whoami():
    """Show the Cookidoo profile you are signed in as.

    Cookidoo returns a profile name, not the email address you signed in with,
    so that is what this prints. `thermomix-cli setup --show` is where you see
    which email and locale this Mac is configured to use.
    """
    async with cookidoo_session() as cookidoo:
        info = await cookidoo.get_user_info()
        table = Table(show_header=False, box=None)
        # Only the fields Cookidoo actually sends back.
        for field in ("username", "description"):
            value = getattr(info, field, None)
            if value is not None:
                table.add_row(field, str(value))
        if not table.row_count:
            console.print("[green]Signed in[/green], but Cookidoo returned no profile details.")
            return
        console.print(table)
        console.print(
            "[dim]That is your Cookidoo profile name. "
            "Run `thermomix-cli setup --show` for the email this Mac uses.[/dim]"
        )


@app.command()
@asyncio_command
async def subscription():
    """Show the Cookidoo subscription on the account."""
    async with cookidoo_session() as cookidoo:
        sub = await cookidoo.get_active_subscription()
        if not sub:
            console.print("[yellow]No active subscription.[/yellow]")
            console.print(
                "Reading recipes still works. Created Recipes need an active "
                "Cookidoo subscription."
            )
            return
        table = Table(show_header=False, box=None)
        for field in ("type", "active", "status", "start_date", "expires"):
            value = getattr(sub, field, None)
            if value is not None:
                table.add_row(field, str(value))
        console.print(table)
        if not sub.active:
            console.print(
                "[yellow]This subscription is not active – Created Recipes will "
                "not work until it is.[/yellow]"
            )
