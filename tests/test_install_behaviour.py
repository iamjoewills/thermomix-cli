"""The install scripts, actually run.

Reading a shell script proves nothing about what it does. These tests run
`install.sh` and `uninstall.sh` against throwaway home folders and check the
outcome someone would actually experience: after a failed update, does the
command they had this morning still work?

The refusal tests are instant – the installer stops before downloading
anything. The rest share one real install, because fetching a private copy of
Python is the slow part and doing it per test would be minutes of nothing.

Skipped automatically when there is no network: these need the real uv and
Python downloads at least once.
"""
from __future__ import annotations

import itertools
import re
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "install.sh"
UNINSTALL = ROOT / "uninstall.sh"

# Only the system directories: no Homebrew, no existing uv, no Python 3.12 on
# the path. What a Mac that has never been developed on would offer.
BARE_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"


def _online() -> bool:
    try:
        socket.create_connection(("github.com", 443), timeout=5).close()
        return True
    except OSError:
        return False


needs_network = pytest.mark.skipif(
    not _online(), reason="the installer downloads uv and Python from GitHub"
)


def run(script: Path, home: Path, *args: str, **env_extra: str):
    """Run one of the scripts with nothing inherited from this machine."""
    env = {
        "HOME": str(home),
        "TMPDIR": str(home / "tmp"),
        "PATH": BARE_PATH,
        "SHELL": "/bin/zsh",
        "TERM": "dumb",
    }
    env.update(env_extra)
    (home / "tmp").mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        ["/bin/bash", str(script), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
    )


def command(home: Path, *args: str):
    """Run the installed shim exactly as the person who installed it would."""
    return subprocess.run(
        [str(home / ".local/bin/thermomix-cli"), *args],
        env={"HOME": str(home), "PATH": BARE_PATH, "TERM": "dumb"},
        capture_output=True,
        text=True,
        timeout=120,
    )


def make_home(tmp_path_factory, name: str) -> Path:
    home = tmp_path_factory.mktemp(name) / "home"
    home.mkdir()
    return home


_broken_counter = itertools.count()


def broken_source(tmp_path: Path) -> Path:
    """A copy of the tool whose dependencies cannot possibly resolve."""
    src = tmp_path / f"broken-source-{next(_broken_counter)}"
    shutil.copytree(ROOT, src, ignore=shutil.ignore_patterns(
        ".git", ".venv", "__pycache__", "*.egg-info", ".pytest_cache", "build", "dist"
    ))
    pyproject = src / "pyproject.toml"
    # Match by package name, not by pinned version: bumping the floor in
    # pyproject.toml must not quietly turn this "broken" source into a working
    # one and leave the rollback tests passing for the wrong reason.
    original = pyproject.read_text(encoding="utf-8")
    swapped = re.sub(
        r'"cookidoo-api[^"]*"',
        '"thermomix-cli-no-such-package-anywhere>=999"',
        original,
    )
    assert swapped != original, "the cookidoo-api dependency was not found to break"
    pyproject.write_text(swapped, encoding="utf-8")
    (src / "requirements.lock").unlink(missing_ok=True)
    return src


# ── refusals: no download, no network, instant ──────────────────────────────

def test_it_refuses_an_app_folder_somebody_else_made(tmp_path):
    home = tmp_path / "home"
    occupied = home / ".local/share/thermomix-cli"
    occupied.mkdir(parents=True)
    (occupied / "precious.txt").write_text("someone else's data")

    result = run(INSTALL, home, THERMOMIX_CLI_SOURCE=str(ROOT))

    assert result.returncode != 0
    assert "was not created by this installer" in result.stderr
    assert (occupied / "precious.txt").read_text() == "someone else's data"
    assert not (home / ".local/bin/thermomix-cli").exists()


def test_it_refuses_a_symlinked_app_folder_instead_of_writing_through_it(tmp_path):
    """The defect: install through the link, then 'remove' only the link."""
    home = tmp_path / "home"
    (home / ".local/share").mkdir(parents=True)
    elsewhere = tmp_path / "somewhere-else"
    elsewhere.mkdir()
    (home / ".local/share/thermomix-cli").symlink_to(elsewhere)

    result = run(INSTALL, home, THERMOMIX_CLI_SOURCE=str(ROOT))

    assert result.returncode != 0
    assert "is a symbolic link" in result.stderr
    assert list(elsewhere.iterdir()) == []


def test_it_refuses_a_symlinked_command_instead_of_replacing_it(tmp_path):
    home = tmp_path / "home"
    (home / ".local/bin").mkdir(parents=True)
    target = tmp_path / "some-other-tool"
    target.write_text("#!/bin/sh\necho other\n")
    (home / ".local/bin/thermomix-cli").symlink_to(target)

    result = run(INSTALL, home, THERMOMIX_CLI_SOURCE=str(ROOT))

    assert result.returncode != 0
    assert "is a symbolic link" in result.stderr
    assert target.read_text() == "#!/bin/sh\necho other\n"


def test_it_refuses_a_command_that_belongs_to_something_else(tmp_path):
    home = tmp_path / "home"
    (home / ".local/bin").mkdir(parents=True)
    other = home / ".local/bin/thermomix-cli"
    other.write_text("#!/bin/sh\necho a different tool\n")

    result = run(INSTALL, home, THERMOMIX_CLI_SOURCE=str(ROOT))

    assert result.returncode != 0
    assert "already exists and is something else" in result.stderr
    assert "a different tool" in other.read_text()


def test_uninstall_leaves_a_symlinked_app_folder_and_its_contents_alone(tmp_path):
    """The other half of the defect: never report 'removed' for a link."""
    home = tmp_path / "home"
    (home / ".local/share").mkdir(parents=True)
    elsewhere = tmp_path / "somewhere-else"
    elsewhere.mkdir()
    (elsewhere / "143mb-of-stuff.txt").write_text("still here")
    (home / ".local/share/thermomix-cli").symlink_to(elsewhere)

    result = run(UNINSTALL, home, "--keep-credentials")

    assert result.returncode == 0
    assert "it is a symbolic link, so it is left alone" in result.stdout
    assert "removed  " not in result.stdout.split("skipped")[0]
    assert (elsewhere / "143mb-of-stuff.txt").read_text() == "still here"


def test_uninstall_leaves_a_foreign_folder_and_command_alone(tmp_path):
    home = tmp_path / "home"
    foreign = home / ".local/share/thermomix-cli"
    foreign.mkdir(parents=True)
    (foreign / "precious.txt").write_text("not ours")
    (home / ".local/bin").mkdir(parents=True)
    shim = home / ".local/bin/thermomix-cli"
    shim.write_text("#!/bin/sh\necho a different tool\n")

    result = run(UNINSTALL, home, "--keep-credentials")

    assert result.returncode == 0
    assert (foreign / "precious.txt").exists()
    assert "a different tool" in shim.read_text()
    assert "was not created by the installer" in result.stdout
    assert "not the installer's launcher" in result.stdout


# ── the real thing: one install, then the scenarios that matter ─────────────

@pytest.fixture(scope="module")
def installed(tmp_path_factory) -> Path:
    """One genuine install into a throwaway home, shared by the tests below."""
    if not _online():
        pytest.skip("the installer downloads uv and Python from GitHub")
    home = tmp_path_factory.mktemp("installed") / "home"
    home.mkdir()
    result = run(INSTALL, home, THERMOMIX_CLI_SOURCE=str(ROOT))
    assert result.returncode == 0, result.stderr or result.stdout
    assert "thermomix-cli 0.3.0" in result.stdout
    return home


@needs_network
def test_a_clean_install_leaves_a_command_that_runs(installed):
    result = command(installed, "version")

    assert result.returncode == 0
    assert "thermomix-cli 0.3.0" in result.stdout
    assert (installed / ".local/share/thermomix-cli/install-receipt.txt").exists()
    assert not (installed / ".local/share/thermomix-cli/venv.prev").exists()


@needs_network
def test_it_adds_exactly_one_line_to_the_shell_profile(installed):
    zshrc = (installed / ".zshrc").read_text()

    assert zshrc.count("# added by thermomix-cli installer") == 1
    assert str(installed / ".local/bin") in zshrc


@needs_network
def test_a_failed_update_leaves_the_working_command_untouched(installed, tmp_path):
    """P1: the defect deleted the venv before the replacement could succeed."""
    before = command(installed, "version")
    assert before.returncode == 0

    result = run(INSTALL, installed, THERMOMIX_CLI_SOURCE=str(broken_source(tmp_path)))

    assert result.returncode != 0, "the broken source should not install"

    # The outcome that matters, checked first: the command they had this
    # morning still runs. Everything else is how well that gets explained.
    after = command(installed, "version")
    assert after.returncode == 0, (
        "the previously working command must still run after a failed update; "
        f"instead: {after.stderr.strip()}"
    )
    assert after.stdout == before.stdout
    assert not (installed / ".local/share/thermomix-cli/venv.prev").exists(), (
        "the parked copy must be moved back, not left beside the live one"
    )
    assert "Could not install" in result.stderr
    assert "still works" in result.stderr, "and the message should say so"


@needs_network
def test_a_failed_update_keeps_the_saved_cookidoo_details(installed, tmp_path):
    config = installed / ".config/thermomix-cli/config.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text('{"email": "keep@example.com", "password": "keep-me"}')
    config.chmod(0o600)

    run(INSTALL, installed, THERMOMIX_CLI_SOURCE=str(broken_source(tmp_path)))

    assert config.exists()
    assert "keep@example.com" in config.read_text()
    assert oct(config.stat().st_mode & 0o777) == "0o600"


@needs_network
def test_the_restored_command_still_works_after_a_second_failed_update(installed, tmp_path):
    """Rollback has to be repeatable, not a one-off."""
    run(INSTALL, installed, THERMOMIX_CLI_SOURCE=str(broken_source(tmp_path)))
    run(INSTALL, installed, THERMOMIX_CLI_SOURCE=str(broken_source(tmp_path)))

    assert command(installed, "version").returncode == 0


@needs_network
def test_an_interrupted_run_that_left_a_parked_copy_is_recovered(installed):
    """Simulates a Ctrl-C between parking and rebuilding."""
    app = installed / ".local/share/thermomix-cli"
    (app / "venv").rename(app / "venv.prev")
    assert command(installed, "version").returncode != 0, "precondition: broken"

    result = run(INSTALL, installed, THERMOMIX_CLI_SOURCE=str(ROOT))

    assert result.returncode == 0, result.stderr
    assert command(installed, "version").returncode == 0
    assert not (app / "venv.prev").exists()


@needs_network
def test_a_successful_update_is_idempotent_and_keeps_credentials(installed):
    config = installed / ".config/thermomix-cli/config.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text('{"email": "keep@example.com", "password": "keep-me"}')
    config.chmod(0o600)

    first = run(INSTALL, installed, THERMOMIX_CLI_SOURCE=str(ROOT))
    second = run(INSTALL, installed, THERMOMIX_CLI_SOURCE=str(ROOT))

    assert first.returncode == 0 and second.returncode == 0
    assert (installed / ".zshrc").read_text().count("# added by thermomix-cli installer") == 1
    assert command(installed, "version").returncode == 0
    assert "keep@example.com" in config.read_text()


@needs_network
def test_the_installed_tool_writes_its_credentials_privately(installed):
    """The whole credential path, through the real installed command."""
    env = {
        "HOME": str(installed),
        "PATH": BARE_PATH,
        "TERM": "dumb",
        "COOKIDOO_EMAIL": "probe@example.com",
        "COOKIDOO_PASSWORD": "probe-password",
        "THERMOMIX_CLI_CONFIG": str(installed / "probe/config.json"),
    }
    written = subprocess.run(
        [
            str(installed / ".local/share/thermomix-cli/venv/bin/python"),
            "-c",
            "from thermomix_cli import config;"
            "p = config.write_config({'email': 'probe@example.com', 'password': 'probe-password'});"
            "print(p)",
        ],
        env=env, capture_output=True, text=True, timeout=120,
    )

    assert written.returncode == 0, written.stderr
    target = installed / "probe/config.json"
    assert oct(target.stat().st_mode & 0o777) == "0o600"
    assert oct(target.parent.stat().st_mode & 0o777) == "0o700"
    assert "probe-password" not in written.stdout


@needs_network
def test_uninstall_removes_its_own_things_and_keeps_credentials_by_default(installed):
    config = installed / ".config/thermomix-cli/config.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text('{"email": "keep@example.com", "password": "keep-me"}')

    result = run(UNINSTALL, installed, "--keep-credentials")

    assert result.returncode == 0
    assert not (installed / ".local/share/thermomix-cli").exists()
    assert not (installed / ".local/bin/thermomix-cli").exists()
    assert "# added by thermomix-cli installer" not in (installed / ".zshrc").read_text()
    assert config.exists(), "credentials go only when explicitly asked for"


@needs_network
def test_uninstall_runs_twice_without_complaint(installed):
    again = run(UNINSTALL, installed, "--keep-credentials")

    assert again.returncode == 0
    assert "not there" in again.stdout


@needs_network
def test_credentials_go_only_when_explicitly_asked_for(installed):
    config = installed / ".config/thermomix-cli/config.json"
    assert config.exists(), "precondition: the previous test kept them"

    result = run(UNINSTALL, installed, "--remove-credentials")

    assert result.returncode == 0
    assert not config.exists()
    assert "removed" in result.stdout


# ── R2: a source folder whose path contains spaces ──────────────────────────

@needs_network
def test_it_installs_from_a_source_folder_whose_path_has_spaces(tmp_path_factory):
    """~/Downloads/Thermomix CLI/ is an ordinary place for a folder to land."""
    base = tmp_path_factory.mktemp("spacey")
    spaced = base / "Thermomix CLI" / "source with spaces"
    shutil.copytree(ROOT, spaced, ignore=shutil.ignore_patterns(
        ".git", ".venv", "__pycache__", "*.egg-info", ".pytest_cache", "build", "dist"
    ))
    assert (spaced / "requirements.lock").exists(), "the lock file is what gets torn in two"
    home = base / "home"
    home.mkdir()

    result = run(INSTALL, home, THERMOMIX_CLI_SOURCE=str(spaced))

    assert result.returncode == 0, result.stderr or result.stdout
    assert command(home, "version").returncode == 0
    assert "Failed to parse" not in (result.stderr + result.stdout)


@needs_network
def test_a_home_folder_whose_path_has_spaces_also_works(tmp_path_factory):
    base = tmp_path_factory.mktemp("spacey-home")
    home = base / "Users and Things" / "home dir"
    home.mkdir(parents=True)

    result = run(INSTALL, home, THERMOMIX_CLI_SOURCE=str(ROOT))

    assert result.returncode == 0, result.stderr or result.stdout
    assert command(home, "version").returncode == 0


# ── R1: a hard kill leaves a good parked copy AND a broken current one ───────

def break_the_current_venv(home: Path) -> None:
    """Leave the launcher in place but gut what it imports.

    This is the state a SIGKILL mid-build produces: the executable bit is still
    there, so any check that trusts it is fooled.
    """
    site = next((home / ".local/share/thermomix-cli/venv/lib").glob("python*/site-packages"))
    shutil.rmtree(site / "thermomix_cli")
    assert (home / ".local/share/thermomix-cli/venv/bin/thermomix-cli").is_file()


@needs_network
def test_a_good_parked_copy_survives_a_broken_current_one_and_a_failing_retry(
    tmp_path_factory, tmp_path
):
    """The proven risk: both present, so the good backup was thrown away.

    Sequence: install cleanly, simulate the hard kill (park the good copy, break
    the current one), then run a failing update. The command must still work.
    """
    home = tmp_path_factory.mktemp("hardkill") / "home"
    home.mkdir()
    assert run(INSTALL, home, THERMOMIX_CLI_SOURCE=str(ROOT)).returncode == 0
    working = command(home, "version").stdout

    app = home / ".local/share/thermomix-cli"
    shutil.copytree(app / "venv", app / "venv.prev", symlinks=True)
    break_the_current_venv(home)
    assert command(home, "version").returncode != 0, "precondition: current is broken"
    assert (app / "venv.prev").is_dir(), "precondition: a good copy is parked"

    result = run(INSTALL, home, THERMOMIX_CLI_SOURCE=str(broken_source(tmp_path)))

    assert result.returncode != 0, "the broken source should not install"
    after = command(home, "version")
    assert after.returncode == 0, (
        "the good parked copy must be recovered, not discarded; "
        f"instead: {after.stderr.strip()}"
    )
    assert after.stdout == working
    assert "putting back the copy an interrupted run left parked" in result.stdout
    assert not (app / "venv.prev").exists()


@needs_network
def test_the_recovered_copy_is_restored_to_its_original_path(tmp_path_factory):
    """A venv has its own path baked into its scripts, so anywhere else is dead."""
    home = tmp_path_factory.mktemp("restore-path") / "home"
    home.mkdir()
    assert run(INSTALL, home, THERMOMIX_CLI_SOURCE=str(ROOT)).returncode == 0

    app = home / ".local/share/thermomix-cli"
    shutil.copytree(app / "venv", app / "venv.prev", symlinks=True)
    break_the_current_venv(home)

    result = run(INSTALL, home, THERMOMIX_CLI_SOURCE=str(ROOT))

    assert result.returncode == 0, result.stderr
    assert (app / "venv").is_dir()
    assert not (app / "venv.prev").exists()
    assert command(home, "version").returncode == 0


@needs_network
def test_a_stale_parked_copy_is_dropped_when_the_current_one_runs(tmp_path_factory):
    """The other direction: do not clobber a working install with an old copy."""
    home = tmp_path_factory.mktemp("stale-prev") / "home"
    home.mkdir()
    assert run(INSTALL, home, THERMOMIX_CLI_SOURCE=str(ROOT)).returncode == 0

    app = home / ".local/share/thermomix-cli"
    shutil.copytree(app / "venv", app / "venv.prev", symlinks=True)

    result = run(INSTALL, home, THERMOMIX_CLI_SOURCE=str(ROOT))

    assert result.returncode == 0, result.stderr
    assert "putting back the copy" not in result.stdout
    assert not (app / "venv.prev").exists()
    assert command(home, "version").returncode == 0


@needs_network
def test_it_never_claims_a_broken_copy_still_works(tmp_path_factory, tmp_path):
    """The message has to be true: nothing runnable was kept, so say that."""
    home = tmp_path_factory.mktemp("truthful") / "home"
    home.mkdir()
    assert run(INSTALL, home, THERMOMIX_CLI_SOURCE=str(ROOT)).returncode == 0
    break_the_current_venv(home)

    result = run(INSTALL, home, THERMOMIX_CLI_SOURCE=str(broken_source(tmp_path)))

    assert result.returncode != 0
    assert "still works" not in result.stderr, "there was nothing working to keep"
    assert "did not run, so nothing was kept" in result.stderr
