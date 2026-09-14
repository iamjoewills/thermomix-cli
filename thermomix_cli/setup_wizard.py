"""The `thermomix-cli setup` wizard – a few questions, then a private file.

Kept deliberately plain: it asks, it saves, it tells you what to run next. The
password is read without echo and is never printed back, not even masked, and
not in the summary at the end.
"""
from __future__ import annotations

import getpass
from dataclasses import dataclass
from typing import Callable

from thermomix_cli import config

Ask = Callable[[str], str]
AskSecret = Callable[[str], str]
Echo = Callable[[str], None]

WARNING = (
    "Cookidoo has no official public API. This tool works by using the same "
    "web requests the Cookidoo website uses, and Vorwerk does not support or "
    "endorse it. It can stop working at any time, without warning."
)


@dataclass(frozen=True)
class SetupResult:
    path: str
    email: str
    country: str
    language: str
    changed_password: bool


class SetupAbandoned(RuntimeError):
    """The wizard could not finish – nothing was saved."""


def _default_ask(prompt: str) -> str:
    return input(prompt)


def _default_ask_secret(prompt: str) -> str:
    return getpass.getpass(prompt)


def _prompt(ask: Ask, question: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = ask(f"{question}{suffix}: ").strip()
    return answer or default


def _prompt_password(ask_secret: AskSecret, echo: Echo, keep_existing: bool) -> str | None:
    """Ask twice and compare, because nothing is echoed back to check.

    Returns None when an existing password should be kept.
    """
    for attempt in range(3):
        hint = " (press Enter to keep the saved one)" if keep_existing else ""
        first = ask_secret(f"Cookidoo password{hint}: ")
        if not first and keep_existing:
            return None
        if not first:
            echo("A password is needed. Try again.")
            continue
        if "\n" in first or "\r" in first:
            echo("That password contains a line break, which cannot be saved. Try again.")
            continue
        second = ask_secret("Type it once more to check: ")
        if first == second:
            return first
        echo("Those two did not match. Try again.")
    raise SetupAbandoned("Password not confirmed after three tries – nothing was saved.")


def run_setup(
    *,
    ask: Ask | None = None,
    ask_secret: AskSecret | None = None,
    echo: Echo | None = None,
) -> SetupResult:
    """Collect Cookidoo details and save them privately."""
    ask = ask or _default_ask
    ask_secret = ask_secret or _default_ask_secret
    echo = echo or print

    existing = config.read_config()
    has_password = bool(existing.get("password"))

    echo("")
    echo("Setting up Thermomix CLI.")
    echo("")
    echo(WARNING)
    echo("")
    echo("You need the email address and password you use to sign in to Cookidoo.")
    echo("Nothing is sent anywhere while you answer – the details are saved on this")
    echo("Mac only, in a file that only your user account can read.")
    echo("")

    email = _prompt(ask, "Cookidoo email address", existing.get("email", ""))
    if not email or "@" not in email:
        raise SetupAbandoned("That does not look like an email address – nothing was saved.")

    password = _prompt_password(ask_secret, echo, keep_existing=has_password)
    changed_password = password is not None
    if password is None:
        password = existing["password"]
    # Register before anything else can fail: from here on, any error message
    # or traceback that happens to carry the password gets it scrubbed out.
    config.register_secret(password)

    echo("")
    echo("Cookidoo serves a different site per country. The defaults suit the UK.")
    echo("If you are elsewhere, `thermomix-cli locale list` shows every option.")
    country = _prompt(ask, "Country code", existing.get("country") or config.DEFAULT_COUNTRY)
    language = _prompt(ask, "Language", existing.get("language") or config.DEFAULT_LANGUAGE)

    path = config.write_config(
        {
            "email": email,
            "password": password,
            "country": country.lower(),
            "language": language,
        }
    )

    echo("")
    echo(f"Saved to {path}")
    echo("Only your user account can read that file. The password is not shown again.")
    if not config.parent_is_private(path):
        echo("")
        echo(f"Note: the folder {path.parent} can be opened by other accounts on")
        echo("this Mac. The file itself is still private. To close the folder too:")
        echo(f"    chmod 700 {path.parent}")
    echo("")
    echo("Now check it works:")
    echo("    thermomix-cli auth login")
    echo("")

    return SetupResult(
        path=str(path),
        email=email,
        country=country.lower(),
        language=language,
        changed_password=changed_password,
    )
