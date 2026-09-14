"""Thermomix CLI entry point."""
from __future__ import annotations

import os
import sys
import traceback

import typer

from thermomix_cli import __version__
from thermomix_cli.commands import (
    auth,
    calendar,
    collection,
    custom_recipe,
    locale,
    recipe,
    setup,
    shopping,
)
from thermomix_cli.config import ConfigError, redact

app = typer.Typer(
    name="thermomix-cli",
    help=(
        "Thermomix / Cookidoo CLI – manage recipes, collections, the week "
        "planner and the shopping list from the command line.\n\n"
        "Cookidoo has no official public API: this is an unofficial tool, not "
        "supported or endorsed by Vorwerk, and it can stop working at any time.\n\n"
        "New here? Run `thermomix-cli setup`."
    ),
    no_args_is_help=True,
)

app.add_typer(setup.app)
app.add_typer(auth.app, name="auth")
app.add_typer(locale.app, name="locale")
app.add_typer(recipe.app, name="recipe")
app.add_typer(custom_recipe.app, name="custom-recipe")
app.add_typer(collection.app, name="collection")
app.add_typer(calendar.app, name="calendar")
app.add_typer(shopping.app, name="shopping")


@app.command()
def version():
    """Show which version of Thermomix CLI is installed."""
    typer.echo(f"thermomix-cli {__version__}")


def _debug_wanted() -> bool:
    return os.environ.get("THERMOMIX_CLI_DEBUG", "").strip() not in ("", "0", "false", "no")


def main() -> None:
    """Console-script entry point.

    Wraps the app so an unexpected failure prints one readable line instead of
    a traceback, and so anything that does get printed has known secrets
    scrubbed out of it first.
    """
    try:
        app()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.stderr.write("\nStopped.\n")
        raise SystemExit(130) from None
    except ConfigError as exc:
        sys.stderr.write(redact(str(exc)) + "\n")
        raise SystemExit(2) from None
    except Exception as exc:  # noqa: BLE001 – the last line of defence
        if _debug_wanted():
            sys.stderr.write(redact("".join(traceback.format_exc())))
        else:
            sys.stderr.write(redact(f"{exc}") + "\n")
            sys.stderr.write(
                "\nSet THERMOMIX_CLI_DEBUG=1 for the technical detail.\n"
            )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
