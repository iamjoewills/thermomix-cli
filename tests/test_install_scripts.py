"""The promises the install and uninstall scripts make, checked as text.

The scripts are also run end to end against a throwaway HOME; these tests are
the cheap guard that the promises stay in the file.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "install.sh"
UNINSTALL = ROOT / "uninstall.sh"


@pytest.fixture(scope="module")
def install() -> str:
    return INSTALL.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def uninstall() -> str:
    return UNINSTALL.read_text(encoding="utf-8")


def test_both_scripts_are_valid_shell():
    for script in (INSTALL, UNINSTALL):
        subprocess.run(["bash", "-n", str(script)], check=True)


def test_both_scripts_stop_on_the_first_error(install, uninstall):
    for text in (install, uninstall):
        assert "set -euo pipefail" in text


def test_the_downloaded_python_installer_is_pinned_and_checksummed(install):
    assert 'UV_VERSION="0.12.13"' in install
    assert "UV_SHA256_ARM64=" in install
    assert "UV_SHA256_X86_64=" in install
    assert "shasum -a 256" in install
    assert "did not match its published checksum" in install


def test_the_python_installer_comes_from_its_official_release_page(install):
    assert "https://github.com/astral-sh/uv/releases/download/" in install


def test_new_installs_come_from_the_public_repository(install):
    assert 'REPO_URL="https://github.com/iamjoewills/thermomix-cli"' in install
    assert 'SOURCE="${THERMOMIX_CLI_SOURCE:-$REPO_URL/archive/' in install


def test_everything_uv_downloads_stays_inside_the_app_folder(install):
    """So an existing uv on the Mac is untouched and uninstall really removes it."""
    for setting in ("UV_PYTHON_INSTALL_DIR", "UV_CACHE_DIR", "UV_TOOL_DIR"):
        assert f'export {setting}="$APP_HOME' in install


def test_the_installer_refuses_a_folder_it_did_not_create(install):
    assert "was not created by this installer" in install
    assert "already exists and is something else" in install


def test_the_installer_never_runs_sudo_or_touches_system_paths(install):
    assert re.search(r"^\s*sudo\s|[;&|]\s*sudo\s", install, re.MULTILINE) is None
    assert "never uses sudo" in install  # it says so, and means it
    assert "/usr/local/bin" not in install
    assert "/Library/" not in install


def test_the_shell_startup_line_is_added_only_once(install):
    assert 'RC_MARKER="# added by thermomix-cli installer"' in install
    assert 'grep -qF "$RC_MARKER"' in install


def test_the_installer_proves_the_command_runs_before_claiming_success(install):
    assert '"$BIN_DIR/thermomix-cli" version' in install
    assert "installed but would not run" in install


def test_the_installer_never_handles_credentials(install):
    """Credentials are the wizard's job. The installer must not read or store any."""
    assert "THERMOMIX_CLI_CONFIG" not in install
    assert ".config/thermomix-cli" not in install
    assert re.search(r"(?i)pass(word|wd)\s*=", install) is None
    assert "read -s" not in install and "getpass" not in install


def test_uninstall_only_removes_what_it_marked(uninstall):
    assert 'MARKER_FILE=".thermomix-cli-install"' in uninstall
    assert 'if [ -e "$APP_HOME/$MARKER_FILE" ]' in uninstall
    assert "it was not created by the installer, so it is left alone" in uninstall
    assert "it is not the installer's launcher, so it is left alone" in uninstall


def test_uninstall_treats_credentials_as_a_separate_explicit_choice(uninstall):
    assert "--remove-credentials" in uninstall
    assert "--keep-credentials" in uninstall
    assert 'CREDENTIALS="keep"' in uninstall


def test_uninstall_says_the_cookidoo_account_is_untouched(uninstall):
    assert "Cookidoo account" in uninstall
    assert "untouched" in uninstall


def test_neither_script_disables_macos_protections(install, uninstall):
    for text in (install, uninstall):
        for danger in ("spctl", "csrutil", "xattr -d", "curl -k", "--insecure"):
            assert danger not in text


def test_the_previous_version_is_parked_not_deleted(install):
    """P1: `rm -rf venv` before the replacement exists destroyed working installs."""
    assert 'mv "$APP_HOME/venv" "$PREV"' in install
    assert 'mv "$PREV" "$APP_HOME/venv"' in install
    assert re.search(r'rm -rf "\$APP_HOME/venv"\s*\n"\$UV_BIN" venv', install) is None


def test_the_rollback_runs_even_on_an_interrupt(install):
    assert "trap cleanup EXIT" in install
    assert '[ "$PARKED" = "1" ] && restore_previous' in install


def test_the_old_copy_is_only_let_go_after_the_command_runs(install):
    prove = install.index('step "Checking it works"')
    assert install.index('rm -rf "$PREV"', prove) > prove
    assert install.index("PARKED=0", prove) > prove


def test_both_scripts_refuse_symlinked_targets(install, uninstall):
    assert '[ -L "$APP_HOME" ]' in install
    assert '[ -L "$BIN_DIR/thermomix-cli" ]' in install
    assert '[ -L "$APP_HOME" ]' in uninstall
    assert '[ -L "$SHIM" ]' in uninstall
    assert "it is a symbolic link, so it is left alone" in uninstall


def test_the_backup_path_is_refused_when_it_is_not_ours(install):
    assert '[ -L "$PREV" ]' in install
    assert '[ -e "$PREV" ] && [ ! -d "$PREV" ]' in install


def test_the_install_uses_the_tested_dependency_versions(install):
    assert "requirements.lock" in install
    assert "--constraint" in install


def test_the_pinned_versions_exist_and_say_how_to_update():
    lock = (ROOT / "requirements.lock").read_text(encoding="utf-8")
    assert "uv pip compile pyproject.toml -o requirements.lock" in lock
    for package in ("cookidoo-api==", "typer==", "rich==", "aiohttp=="):
        assert package in lock


def test_the_constraint_flag_is_an_array_not_a_word_split_string(install):
    """R2: a source folder named 'Thermomix CLI' tore the flag in two."""
    assert "CONSTRAINTS=()" in install
    assert 'CONSTRAINTS=(--constraint requirements.lock)' in install
    assert re.search(r'CONSTRAINTS="--constraint', install) is None
    # bash 3.2 needs the guarded form for an empty array under `set -u`.
    assert '${CONSTRAINTS[@]+"${CONSTRAINTS[@]}"}' in install


def test_the_constraint_is_passed_as_a_bare_filename(install):
    """uv splits a --constraint path on spaces whatever the shell does."""
    assert 'cd "$SRC_DIR" && "$UV_BIN" pip install' in install
    assert "--constraint requirements.lock" in install
    assert '--constraint "$SRC_DIR' not in install


def test_the_parked_copy_is_judged_by_running_it(install):
    """R1: the executable bit survives a half-built environment; imports do not."""
    assert "venv_runs()" in install
    assert '"$APP_HOME/venv/bin/thermomix-cli" version >/dev/null 2>&1' in install
    # Recovery must not hinge on the current folder merely being absent.
    assert re.search(r'\[ -d "\$PREV" \] && \[ ! -d "\$APP_HOME/venv" \]', install) is None


def test_a_broken_current_copy_is_never_described_as_working(install):
    assert "did not run, so nothing was kept" in install
    prove = install.index("if venv_runs; then\n    mv")
    assert install.index("still works", prove) > prove
