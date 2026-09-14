"""This repository is published. Nothing private may travel with it.

These tests read the shipped files as text and fail on anything that ties the
tool to one person's machine, plugins or account.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SHIPPED_SUFFIXES = {".py", ".sh", ".toml", ".md", ".cfg", ".txt", ".json", ".yml", ".yaml"}
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "build", "dist"}
# The two scanner files spell out the very patterns they hunt for, so scanning
# them would only ever find themselves.
SCANNERS = {"test_public_source.py", "test_install_scripts.py"}


def shipped_files(*, include_tests: bool = True) -> list[Path]:
    found = []
    for path in ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not include_tests and "tests" in path.parts:
            continue
        if path.is_file() and path.suffix in SHIPPED_SUFFIXES and path.name not in SCANNERS:
            found.append(path)
    return sorted(found)


def read_all(**kwargs) -> dict[Path, str]:
    return {p: p.read_text(encoding="utf-8", errors="replace") for p in shipped_files(**kwargs)}


@pytest.fixture(scope="module")
def sources() -> dict[Path, str]:
    """Everything published, tests included."""
    return read_all()


@pytest.fixture(scope="module")
def product() -> dict[Path, str]:
    """Everything published except the tests.

    A test that asserts "this word must not appear" has to contain the word.
    Coupling checks therefore read the product; credential and identity checks
    below read everything, tests included.
    """
    return read_all(include_tests=False)


def offenders(sources, pattern, *, allow=(), flags=re.IGNORECASE):
    rx = re.compile(pattern, flags)
    hits = []
    for path, text in sources.items():
        if path.name in allow:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                hits.append(f"{path.relative_to(ROOT)}:{line_no}: {line.strip()[:120]}")
    return hits


def test_the_test_suite_can_see_the_shipped_files(sources, product):
    assert {"install.sh", "uninstall.sh", "pyproject.toml", "README.md", "SETUP.md"} <= {
        p.name for p in product
    }
    assert any(p.name.startswith("test_") for p in sources)


def test_no_home_directory_of_any_particular_person(sources):
    assert offenders(sources, r"/Users/[a-z0-9._-]+/") == []


def test_no_private_plugin_or_workspace_dependency(product):
    assert offenders(product, r"\bclova\b|CLAUDE_PLUGIN|joe-plugins|carvable") == []
    assert offenders(product, r"\bDots\b", flags=0) == []


def test_no_dots_sync_command_is_exposed(product):
    assert offenders(product, r"sync[_-]dots|dots_compiler") == []


def test_no_credentials_are_committed(sources):
    patterns = [
        r"password\s*[=:]\s*[\"'][^\"'{}<$]{6,}[\"']",
        r"\bBearer\s+[A-Za-z0-9._-]{12,}",
        r"\bsk-[A-Za-z0-9]{16,}",
        r"\bghp_[A-Za-z0-9]{20,}",
    ]
    # The credential tests deliberately carry obvious fake passwords.
    allow = {"test_setup_wizard.py", "test_config.py", "test_error_output.py"}
    for pattern in patterns:
        assert offenders(sources, pattern, allow=allow) == [], pattern


def test_no_real_cookidoo_account_or_recipe_identifiers(sources):
    # A Cookidoo customer recipe id is a 26-character ULID; an authorId is a UUID.
    ulid = r"\b01[0-9A-HJKMNP-TV-Z]{24}\b"
    uuid = r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
    assert offenders(sources, ulid) == []
    assert offenders(sources, f"authorId|{uuid}") == []


def test_no_third_party_api_keys_are_embedded(sources):
    assert offenders(sources, r"api[_-]?key\s*[=:]\s*[\"']?[A-Za-z0-9]{10,}") == []


def test_no_personal_email_addresses(sources):
    hits = offenders(sources, r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    permitted = re.compile(r"example\.com|example\.org|cookidoo|noreply", re.IGNORECASE)
    assert [h for h in hits if not permitted.search(h)] == []


def test_no_bundled_recipe_data(sources):
    assert not (ROOT / "recipes").exists()


def test_nothing_shipped_ever_runs_sudo(sources):
    """Saying "this never uses sudo" in prose is fine; running it is not."""
    assert offenders(sources, r"^\s*sudo\s|[;&|]\s*sudo\s|\$\(\s*sudo\s") == []


def test_the_installer_never_weakens_macos_security(sources):
    assert offenders(sources, r"spctl|csrutil|xattr\s+-d|--no-verify|--insecure|curl\s+-k\b") == []


def test_no_unbounded_delete_of_a_home_or_root_path(sources):
    bad = offenders(sources, r"rm\s+-rf\s+[\"']?(/|~|\$HOME)[\"']?\s*$")
    bad += offenders(sources, r"rm\s+-rf\s+[\"']?\$\{?HOME\}?/[\"']?\s*$")
    assert bad == []


def test_the_unofficial_api_warning_is_in_the_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "no official public API" in readme
    assert "Vorwerk" in readme
    # The warning must come before the install instructions.
    assert readme.index("no official public API") < readme.index("install.sh")


def test_upstream_attribution_is_kept():
    notice = (ROOT / "NOTICE.md").read_text(encoding="utf-8")
    for credit in ("cookidoo-api", "Typer", "Rich", "aiohttp", "uv"):
        assert credit in notice


def test_no_licence_is_claimed_that_the_repository_does_not_carry(sources):
    """Say what is true, whichever way the owner decides later.

    Nothing here requires the absence of a licence file. If one is added, a
    named set of terms simply has to have a real file behind it.
    """
    has_licence_file = any(
        (ROOT / name).exists() for name in ("LICENSE", "LICENSE.md", "LICENCE", "LICENCE.md")
    )
    named = offenders(sources, r"\bMIT licen[cs]e|Apache-2|GPL-3|BSD-3")
    if not has_licence_file:
        assert named == [], "a licence is named but no licence file exists"


def test_personal_use_is_permitted_without_granting_anything_wider():
    """The owner has allowed installing and running it. Nothing more."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    notice = (ROOT / "NOTICE.md").read_text(encoding="utf-8")

    def flat(text: str) -> str:
        """Markdown wraps these sentences across lines; the words are the point."""
        return " ".join(text.split())

    for name, text in (("README.md", flat(readme)), ("NOTICE.md", flat(notice))):
        assert "install and run this tool for personal use" in text, name
        assert "All other rights are reserved" in text, name
        assert "dependencies retain their own licences" in text, name

    # The permission is narrow on purpose: nothing may read as redistribution,
    # commercial use, or a licence the owner has not chosen.
    for text in (readme, notice):
        assert not re.search(r"free to (redistribute|share|sell)|commercial use|open source", text, re.I)


def test_the_guide_does_not_gate_the_reader_behind_asking_permission():
    setup = (ROOT / "SETUP.md").read_text(encoding="utf-8")

    assert "install and run this tool for personal use" in setup
    assert "ask first" not in setup.lower()
