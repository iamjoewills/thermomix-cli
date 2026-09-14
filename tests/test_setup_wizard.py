"""The wizard, driven by fake answers – no terminal, no network, no real account."""
from __future__ import annotations

import os
import stat

import pytest

from thermomix_cli import config
from thermomix_cli.setup_wizard import SetupAbandoned, run_setup

PASSWORD = "correct-horse-battery-staple"


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    target = tmp_path / "cfg" / "config.json"
    monkeypatch.setenv(config.CONFIG_ENV_VAR, str(target))
    for leaked in ("COOKIDOO_EMAIL", "COOKIDOO_PASSWORD", "COOKIDOO_COUNTRY", "COOKIDOO_LANGUAGE"):
        monkeypatch.delenv(leaked, raising=False)
    return target


class Transcript:
    """Stands in for a person at a keyboard, and records everything shown."""

    def __init__(self, answers, secrets):
        self.answers = list(answers)
        self.secrets = list(secrets)
        self.shown: list[str] = []
        self.prompts: list[str] = []

    def ask(self, prompt):
        self.prompts.append(prompt)
        return self.answers.pop(0)

    def ask_secret(self, prompt):
        self.prompts.append(prompt)
        return self.secrets.pop(0)

    def echo(self, line):
        self.shown.append(str(line))

    @property
    def everything_shown(self):
        return "\n".join(self.shown + self.prompts)


def run(answers, secrets):
    t = Transcript(answers, secrets)
    result = run_setup(ask=t.ask, ask_secret=t.ask_secret, echo=t.echo)
    return t, result


def test_a_complete_run_saves_a_private_file(isolated_config):
    transcript, result = run(["cook@example.com", "gb", "en-GB"], [PASSWORD, PASSWORD])

    assert isolated_config.exists()
    assert stat.S_IMODE(isolated_config.stat().st_mode) == 0o600
    assert result.email == "cook@example.com"
    assert result.changed_password is True
    assert config.load_credentials().password == PASSWORD
    assert "thermomix-cli auth login" in transcript.everything_shown


def test_the_password_is_never_shown_back(isolated_config):
    transcript, _ = run(["cook@example.com", "gb", "en-GB"], [PASSWORD, PASSWORD])

    assert PASSWORD not in transcript.everything_shown


def test_the_password_is_not_in_the_result_object(isolated_config):
    _, result = run(["cook@example.com", "gb", "en-GB"], [PASSWORD, PASSWORD])

    assert PASSWORD not in repr(result)


def test_the_unofficial_api_warning_comes_before_any_question(isolated_config):
    transcript, _ = run(["cook@example.com", "gb", "en-GB"], [PASSWORD, PASSWORD])

    warning_line = next(i for i, line in enumerate(transcript.shown) if "no official public API" in line)
    assert warning_line < len(transcript.shown)
    assert "Vorwerk does not support or endorse it" in transcript.everything_shown
    # The first thing asked for is the email, and the warning was already shown.
    assert transcript.prompts[0].startswith("Cookidoo email address")


def test_a_mistyped_password_is_asked_again_not_accepted(isolated_config):
    transcript, _ = run(
        ["cook@example.com", "gb", "en-GB"],
        ["typo-one", "typo-two", PASSWORD, PASSWORD],
    )

    assert "did not match" in transcript.everything_shown
    assert config.load_credentials().password == PASSWORD


def test_three_mismatches_save_nothing(isolated_config):
    t = Transcript(["cook@example.com"], ["a", "b", "c", "d", "e", "f"])

    with pytest.raises(SetupAbandoned):
        run_setup(ask=t.ask, ask_secret=t.ask_secret, echo=t.echo)

    assert not isolated_config.exists()


def test_a_bad_email_saves_nothing(isolated_config):
    t = Transcript(["not-an-email"], [])

    with pytest.raises(SetupAbandoned):
        run_setup(ask=t.ask, ask_secret=t.ask_secret, echo=t.echo)

    assert not isolated_config.exists()


def test_a_password_with_a_line_break_is_refused(isolated_config):
    transcript, _ = run(
        ["cook@example.com", "gb", "en-GB"],
        ["bad\npassword", PASSWORD, PASSWORD],
    )

    assert "line break" in transcript.everything_shown
    assert config.load_credentials().password == PASSWORD


def test_rerunning_can_keep_the_existing_password(isolated_config):
    run(["cook@example.com", "gb", "en-GB"], [PASSWORD, PASSWORD])

    transcript, result = run(["new@example.com", "de", "de-DE"], [""])

    assert result.changed_password is False
    creds = config.load_credentials()
    assert creds.email == "new@example.com"
    assert creds.country == "de"
    assert creds.password == PASSWORD
    assert PASSWORD not in transcript.everything_shown


def test_defaults_suit_someone_who_just_presses_enter(isolated_config):
    _, result = run(["cook@example.com", "", ""], [PASSWORD, PASSWORD])

    assert result.country == config.DEFAULT_COUNTRY
    assert result.language == config.DEFAULT_LANGUAGE


def test_the_password_is_scrubbable_before_anything_is_written(isolated_config, monkeypatch):
    """The proven defect: registered after the write, so inert during it."""
    registered_at_write_time = {}

    real_write = config.write_config

    def watching_write(values):
        registered_at_write_time["yes"] = "********" in config.redact(f"x{PASSWORD}x")
        return real_write(values)

    monkeypatch.setattr(config, "write_config", watching_write)
    run(["cook@example.com", "gb", "en-GB"], [PASSWORD, PASSWORD])

    assert registered_at_write_time["yes"] is True


def test_a_kept_existing_password_is_also_scrubbable(isolated_config, monkeypatch):
    run(["cook@example.com", "gb", "en-GB"], [PASSWORD, PASSWORD])
    config._SECRETS.clear()

    seen = {}
    real_write = config.write_config

    def watching_write(values):
        seen["registered"] = "********" in config.redact(f"x{PASSWORD}x")
        return real_write(values)

    monkeypatch.setattr(config, "write_config", watching_write)
    run(["cook@example.com", "gb", "en-GB"], [""])

    assert seen["registered"] is True


def test_it_warns_when_the_surrounding_folder_is_open_to_others(tmp_path, monkeypatch):
    shared = tmp_path / "shared"
    shared.mkdir(mode=0o755)
    os.chmod(shared, 0o755)
    monkeypatch.setenv(config.CONFIG_ENV_VAR, str(shared / "config.json"))

    transcript, _ = run(["cook@example.com", "gb", "en-GB"], [PASSWORD, PASSWORD])

    assert "can be opened by other accounts" in transcript.everything_shown
    assert "chmod 700" in transcript.everything_shown
    assert PASSWORD not in transcript.everything_shown
