"""Where the CLI keeps your Cookidoo details, and how it keeps them private.

Everything lives in one JSON file that only your user account can read
(`~/.config/thermomix-cli/config.json`, mode 0600 inside a 0700 directory).
Nothing is written anywhere else, and the password is never printed.
"""
from __future__ import annotations

import json
import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path

CONFIG_ENV_VAR = "THERMOMIX_CLI_CONFIG"
DEFAULT_CONFIG_DIR = Path("~/.config/thermomix-cli")
CONFIG_FILE_NAME = "config.json"

DEFAULT_COUNTRY = "gb"
DEFAULT_LANGUAGE = "en-GB"

_DIR_MODE = 0o700
_FILE_MODE = 0o600

# Every secret the process has handled, so error text can be scrubbed before
# it reaches a terminal, a log or a bug report.
_SECRETS: set[str] = set()


class ConfigError(RuntimeError):
    """The configuration is missing or unusable."""


@dataclass(frozen=True)
class Credentials:
    email: str
    password: str
    country: str = DEFAULT_COUNTRY
    language: str = DEFAULT_LANGUAGE


def config_path() -> Path:
    """The config file this run will use."""
    override = os.environ.get(CONFIG_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return DEFAULT_CONFIG_DIR.expanduser() / CONFIG_FILE_NAME


def register_secret(value: str | None) -> None:
    """Remember a value that must never appear in output."""
    if value:
        _SECRETS.add(value)


def redact(text: str) -> str:
    """Replace any known secret in `text` with a marker.

    Used on every error message and traceback the CLI prints, so a password
    cannot escape through an exception raised deep inside a dependency.
    """
    for secret in sorted(_SECRETS, key=len, reverse=True):
        if secret:
            text = text.replace(secret, "********")
    return text


def read_config() -> dict[str, str]:
    """Read the saved settings, or return an empty dict when there are none."""
    path = config_path()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ConfigError(
            f"{path} could not be read ({exc.__class__.__name__}). "
            "Run `thermomix-cli setup` to write it again."
        ) from None
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} is not a settings file. Run `thermomix-cli setup`.")
    return {str(k): "" if v is None else str(v) for k, v in raw.items()}


def write_config(values: dict[str, str]) -> Path:
    """Write the settings so only this user account can read them.

    A password is about to be written, so this refuses anything ambiguous
    rather than guessing: a config path that is a symbolic link could send the
    password somewhere else entirely, and a directory somebody else made is
    not ours to lock down.
    """
    path = config_path()
    if path.is_symlink():
        raise ConfigError(
            f"{path} is a symbolic link, so this would write your password "
            "somewhere other than where it appears to go. Nothing was saved.\n"
            "Remove the link, or point THERMOMIX_CLI_CONFIG at a real file."
        )

    parent = path.parent
    created_parent = not parent.exists()
    parent.mkdir(parents=True, exist_ok=True)
    if created_parent:
        # Only tighten the folder we just made. An existing one belongs to
        # someone – possibly to something else entirely – so it is left as is
        # and reported by `setup --show` instead.
        os.chmod(parent, _DIR_MODE)

    # mkstemp creates with O_CREAT|O_EXCL at mode 0600: a random name that
    # cannot collide with a stale file, and cannot be pre-planted as a symlink
    # for the password to travel down.
    fd, tmp_name = tempfile.mkstemp(dir=parent, prefix=path.name + ".", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(values, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.chmod(tmp, _FILE_MODE)
        # os.replace does not follow a link at the destination, so an existing
        # config.json that is a symlink is replaced rather than written through.
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return path


def forget_config() -> bool:
    """Delete the saved settings. Returns True if a file was removed."""
    path = config_path()
    if not path.exists():
        return False
    path.unlink()
    return True


def file_is_private(path: Path | None = None) -> bool:
    """True when the config file cannot be read by anyone else on the Mac.

    A symbolic link counts as not private: what it points at can change under
    you, so the permissions you can see are not the ones that apply.
    """
    target = path or config_path()
    if target.is_symlink() or not target.exists():
        return False
    mode = stat.S_IMODE(target.stat().st_mode)
    return mode & 0o077 == 0


def parent_is_private(path: Path | None = None) -> bool:
    """True when the folder holding the config is closed to other accounts."""
    parent = (path or config_path()).parent
    if not parent.exists():
        return False
    return stat.S_IMODE(parent.stat().st_mode) & 0o077 == 0


def load_credentials() -> Credentials:
    """The details needed to talk to Cookidoo.

    Environment variables win over the saved file, so a script can pass details
    in without touching the config. `COOKIDOO_PASSWORD` is the only accepted
    password variable – a bare `PASSWORD` in the shell is too easy to set by
    accident for something that signs you into an account.
    """
    saved = read_config()
    email = os.environ.get("COOKIDOO_EMAIL") or saved.get("email", "")
    password = os.environ.get("COOKIDOO_PASSWORD") or saved.get("password", "")
    country = os.environ.get("COOKIDOO_COUNTRY") or saved.get("country") or DEFAULT_COUNTRY
    language = os.environ.get("COOKIDOO_LANGUAGE") or saved.get("language") or DEFAULT_LANGUAGE

    if not email or not password:
        raise ConfigError(
            "No Cookidoo details saved yet.\n"
            "Run:  thermomix-cli setup"
        )

    register_secret(password)
    return Credentials(
        email=email,
        password=password,
        country=country.lower(),
        language=language,
    )
