"""What someone gets when they type the command, without touching the network."""
from __future__ import annotations

import contextlib
import inspect
import socket
from unittest.mock import create_autospec

import pytest
from typer.testing import CliRunner

from thermomix_cli import config
from thermomix_cli.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    target = tmp_path / "cfg" / "config.json"
    monkeypatch.setenv(config.CONFIG_ENV_VAR, str(target))
    for leaked in ("COOKIDOO_EMAIL", "COOKIDOO_PASSWORD", "COOKIDOO_COUNTRY", "COOKIDOO_LANGUAGE"):
        monkeypatch.delenv(leaked, raising=False)
    return target


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Block outbound connections, but leave sockets working.

    asyncio builds its event loop out of a socketpair, so replacing the socket
    class itself would break the loop rather than prove anything.
    """
    def refuse(*args, **kwargs):
        raise AssertionError("this command must not open a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def test_help_lists_the_everyday_command_groups():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for group in ("setup", "auth", "recipe", "custom-recipe", "collection", "calendar", "shopping"):
        assert group in result.output


def test_help_carries_the_unofficial_api_warning():
    result = runner.invoke(app, ["--help"])

    assert "no official public API" in result.output
    assert "Vorwerk" in result.output


def test_help_points_a_newcomer_at_setup():
    result = runner.invoke(app, ["--help"])

    assert "thermomix-cli setup" in result.output


def test_there_is_no_dots_command():
    result = runner.invoke(app, ["custom-recipe", "--help"])

    assert result.exit_code == 0
    assert "sync-dots" not in result.output
    assert "dots" not in result.output.lower()


def test_version_prints_without_any_account(isolated_config):
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "thermomix-cli" in result.output


def test_show_before_setup_explains_what_to_run(isolated_config):
    result = runner.invoke(app, ["setup", "--show"])

    assert result.exit_code == 1
    assert "thermomix-cli setup" in result.output


def test_show_after_setup_never_prints_the_password(isolated_config):
    config.write_config({"email": "cook@example.com", "password": "top-secret-pw", "country": "gb"})

    result = runner.invoke(app, ["setup", "--show"])

    assert result.exit_code == 0
    assert "cook@example.com" in result.output
    assert "top-secret-pw" not in result.output
    assert "saved" in result.output


def test_show_warns_when_the_file_is_readable_by_others(isolated_config):
    config.write_config({"email": "cook@example.com", "password": "top-secret-pw"})
    isolated_config.chmod(0o644)

    result = runner.invoke(app, ["setup", "--show"])

    assert "Other accounts on this Mac can read that file" in result.output


def test_forget_removes_the_saved_details_and_repeats_safely(isolated_config):
    config.write_config({"email": "cook@example.com", "password": "top-secret-pw"})

    first = runner.invoke(app, ["setup", "--forget"])
    second = runner.invoke(app, ["setup", "--forget"])

    assert first.exit_code == 0
    assert not isolated_config.exists()
    assert second.exit_code == 0
    assert "Nothing to delete" in second.output


def test_an_account_command_without_setup_says_what_to_do(isolated_config):
    """It must fail on the missing config, not by trying to reach Cookidoo."""
    result = runner.invoke(app, ["auth", "whoami"])

    assert result.exit_code != 0
    assert isinstance(result.exception, (config.ConfigError, SystemExit))
    if isinstance(result.exception, config.ConfigError):
        assert "thermomix-cli setup" in str(result.exception)


def test_deleting_a_recipe_asks_first(isolated_config):
    config.write_config({"email": "cook@example.com", "password": "top-secret-pw"})

    result = runner.invoke(app, ["custom-recipe", "remove", "abc123"], input="n\n")

    assert result.exit_code != 0
    assert "Delete created recipe abc123?" in result.output


# ── custom-recipe list, dispatched through the CLI against a fake API ────────
#
# The defect these guard: the command asked for `get_custom_recipes`, which the
# pinned library does not have, so an advertised command always printed a
# warning instead of listing anything. No network, no account, no real recipes.

class FakeCookidoo:
    """Only what cookidoo-api 0.18.3 actually exposes for this command."""

    def __init__(self, recipes):
        self._recipes = recipes
        self.calls = 0

    async def list_custom_recipes(self):
        self.calls += 1
        return self._recipes


class FakeRecipe:
    def __init__(self, id, name):
        self.id = id
        self.name = name


@contextlib.asynccontextmanager
async def fake_session(fake):
    yield fake


def dispatch_list(monkeypatch, fake):
    from thermomix_cli.commands import custom_recipe

    monkeypatch.setattr(custom_recipe, "cookidoo_session", lambda: fake_session(fake))
    return runner.invoke(app, ["custom-recipe", "list"])


def test_the_pinned_library_really_has_the_method_the_command_calls():
    """If cookidoo-api renames it again, fail here rather than in someone's kitchen."""
    from cookidoo_api import Cookidoo

    method = getattr(Cookidoo, "list_custom_recipes", None)
    assert method is not None, "cookidoo-api no longer exposes list_custom_recipes"
    assert inspect.iscoroutinefunction(method)
    assert list(inspect.signature(method).parameters) == ["self"]
    assert not hasattr(Cookidoo, "get_custom_recipes"), (
        "get_custom_recipes exists after all — the command should use it"
    )


def test_listing_created_recipes_prints_them(isolated_config, monkeypatch):
    config.write_config({"email": "cook@example.com", "password": "pw"})
    fake = FakeCookidoo([FakeRecipe("r-one", "Tomato soup"), FakeRecipe("r-two", "Focaccia")])

    result = dispatch_list(monkeypatch, fake)

    assert result.exit_code == 0, result.output
    assert "Tomato soup" in result.output
    assert "Focaccia" in result.output
    assert "r-one" in result.output
    assert fake.calls == 1, "the API is asked exactly once"


def test_listing_with_nothing_created_says_so_rather_than_warning(isolated_config, monkeypatch):
    config.write_config({"email": "cook@example.com", "password": "pw"})
    fake = FakeCookidoo([])

    result = dispatch_list(monkeypatch, fake)

    assert result.exit_code == 0, result.output
    assert "No created recipes yet" in result.output
    assert fake.calls == 1


def test_listing_no_longer_excuses_itself_with_a_version_warning(isolated_config, monkeypatch):
    """The old output when the best-effort lookup found nothing."""
    config.write_config({"email": "cook@example.com", "password": "pw"})

    result = dispatch_list(monkeypatch, FakeCookidoo([FakeRecipe("r-one", "Tomato soup")]))

    assert "no list method" not in result.output
    assert "cookidoo-api" not in result.output


def test_the_command_calls_the_supported_method_by_name(isolated_config, monkeypatch):
    """An autospec of the real class: a changed signature fails the call."""
    from cookidoo_api import Cookidoo

    stub = create_autospec(Cookidoo, instance=True, spec_set=True)
    stub.list_custom_recipes.return_value = [FakeRecipe("r-one", "Tomato soup")]
    config.write_config({"email": "cook@example.com", "password": "pw"})

    result = dispatch_list(monkeypatch, stub)

    assert result.exit_code == 0, result.output
    assert "Tomato soup" in result.output
    stub.list_custom_recipes.assert_awaited_once_with()
