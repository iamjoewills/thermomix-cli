"""The first-run wizard, and the two things you can do to what it saved."""
from __future__ import annotations

import typer
from rich.console import Console

from thermomix_cli import config
from thermomix_cli.setup_wizard import SetupAbandoned, run_setup

app = typer.Typer()
console = Console()


@app.command("setup")
def setup(
    show: bool = typer.Option(
        False, "--show", help="Show the saved settings (never the password)"
    ),
    forget: bool = typer.Option(
        False, "--forget", help="Delete the saved Cookidoo details from this Mac"
    ),
):
    """Save your Cookidoo details, or show and delete what is saved."""
    if show and forget:
        console.print("[red]Choose one of --show or --forget.[/red]")
        raise typer.Exit(2)

    if show:
        path = config.config_path()
        saved = config.read_config()
        if not saved:
            console.print(f"Nothing saved yet ({path} does not exist).")
            console.print("Run [bold]thermomix-cli setup[/bold] to get started.")
            raise typer.Exit(1)
        console.print(f"File:     {path}")
        console.print(f"Private:  {'yes' if config.file_is_private() else 'NO – see below'}")
        console.print(f"Email:    {saved.get('email', '(not set)')}")
        console.print(f"Password: {'saved' if saved.get('password') else '(not set)'}")
        console.print(f"Country:  {saved.get('country', config.DEFAULT_COUNTRY)}")
        console.print(f"Language: {saved.get('language', config.DEFAULT_LANGUAGE)}")
        if not config.file_is_private():
            console.print(
                "\n[yellow]Other accounts on this Mac can read that file.[/yellow]\n"
                f"Fix it with:  chmod 600 {path}"
            )
        return

    if forget:
        path = config.config_path()
        if config.forget_config():
            console.print(f"[green]Deleted[/green] {path}")
            console.print("Your Cookidoo account itself is untouched.")
        else:
            console.print(f"Nothing to delete ({path} does not exist).")
        return

    try:
        run_setup()
    except SetupAbandoned as exc:
        console.print(f"[yellow]{exc}[/yellow]")
        raise typer.Exit(1) from None
    except (EOFError, KeyboardInterrupt):
        console.print("\n[yellow]Setup stopped – nothing was saved.[/yellow]")
        raise typer.Exit(1) from None
