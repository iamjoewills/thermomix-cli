"""What the settings file must guarantee: private, correct, and removable."""
from __future__ import annotations

import json
import os
import stat

import pytest

from thermomix_cli import config


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    target = tmp_path / "cfg" / "config.json"
    monkeypatch.setenv(config.CONFIG_ENV_VAR, str(target))
    for leaked in ("COOKIDOO_EMAIL", "COOKIDOO_PASSWORD", "COOKIDOO_COUNTRY", "COOKIDOO_LANGUAGE"):
        monkeypatch.delenv(leaked, raising=False)
    return target


def test_saved_details_can_only_be_read_by_this_user(isolated_config):
    path = config.write_config({"email": "cook@example.com", "password": "hunter2"})

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert config.file_is_private() is True


def test_a_loosened_file_is_reported_as_not_private(isolated_config):
    path = config.write_config({"email": "cook@example.com", "password": "hunter2"})
    os.chmod(path, 0o644)

    assert config.file_is_private() is False


def test_no_temporary_file_is_left_behind_holding_the_password(isolated_config):
    config.write_config({"email": "cook@example.com", "password": "hunter2"})

    leftovers = [p.name for p in isolated_config.parent.iterdir() if p.name != "config.json"]
    assert leftovers == []


def test_details_survive_a_round_trip(isolated_config):
    config.write_config(
        {"email": "cook@example.com", "password": "p@ss word", "country": "de", "language": "de-DE"}
    )

    creds = config.load_credentials()
    assert creds.email == "cook@example.com"
    assert creds.password == "p@ss word"
    assert creds.country == "de"
    assert creds.language == "de-DE"


def test_unusual_password_characters_are_stored_exactly(isolated_config):
    awkward = 'a"b\\c$d\'e#f =g😀'
    config.write_config({"email": "cook@example.com", "password": awkward})

    assert config.load_credentials().password == awkward


def test_missing_details_say_what_to_run(isolated_config):
    with pytest.raises(config.ConfigError) as excinfo:
        config.load_credentials()

    assert "thermomix-cli setup" in str(excinfo.value)


def test_environment_wins_over_the_saved_file(isolated_config, monkeypatch):
    config.write_config({"email": "saved@example.com", "password": "saved-pass"})
    monkeypatch.setenv("COOKIDOO_EMAIL", "env@example.com")
    monkeypatch.setenv("COOKIDOO_PASSWORD", "env-pass")

    creds = config.load_credentials()
    assert creds.email == "env@example.com"
    assert creds.password == "env-pass"


def test_a_stray_PASSWORD_variable_is_ignored(isolated_config, monkeypatch):
    """A bare PASSWORD in someone's shell must never be used to sign in."""
    config.write_config({"email": "saved@example.com", "password": "saved-pass"})
    monkeypatch.setenv("PASSWORD", "not-the-one")
    monkeypatch.setenv("EMAIL", "not-the-one@example.com")

    creds = config.load_credentials()
    assert creds.password == "saved-pass"
    assert creds.email == "saved@example.com"


def test_forgetting_is_explicit_and_repeatable(isolated_config):
    config.write_config({"email": "cook@example.com", "password": "hunter2"})

    assert config.forget_config() is True
    assert not isolated_config.exists()
    assert config.forget_config() is False


def test_a_damaged_file_is_explained_not_crashed(isolated_config):
    isolated_config.parent.mkdir(parents=True, exist_ok=True)
    isolated_config.write_text("this is not json")

    with pytest.raises(config.ConfigError) as excinfo:
        config.read_config()

    assert "thermomix-cli setup" in str(excinfo.value)


def test_a_known_password_is_scrubbed_from_any_message(isolated_config):
    config.register_secret("s3cr3t-value")

    scrubbed = config.redact("aiohttp error: password=s3cr3t-value rejected")
    assert "s3cr3t-value" not in scrubbed
    assert "********" in scrubbed


def test_loading_credentials_registers_them_for_scrubbing(isolated_config):
    config.write_config({"email": "cook@example.com", "password": "zz-unique-pw-zz"})
    config.load_credentials()

    assert "zz-unique-pw-zz" not in config.redact("boom: zz-unique-pw-zz")


def test_the_saved_file_is_plain_json_the_owner_can_inspect(isolated_config):
    config.write_config({"email": "cook@example.com", "password": "hunter2"})

    parsed = json.loads(isolated_config.read_text())
    assert parsed["email"] == "cook@example.com"


def test_a_pre_planted_temp_file_cannot_capture_the_password(isolated_config):
    """The temp name must not be guessable, and a collision must not be written."""
    isolated_config.parent.mkdir(parents=True, exist_ok=True)
    decoy = isolated_config.with_name(isolated_config.name + ".tmp")
    decoy.write_text("do not overwrite me")

    config.write_config({"email": "cook@example.com", "password": "sneaky-secret"})

    assert decoy.read_text() == "do not overwrite me"
    assert config.load_credentials().password == "sneaky-secret"


def test_a_symlinked_temp_target_never_receives_the_password(isolated_config, tmp_path):
    """The proven defect: config.json.tmp planted as a link to somebody's file."""
    isolated_config.parent.mkdir(parents=True, exist_ok=True)
    victim = tmp_path / "someone-elses-file.txt"
    victim.write_text("original contents")
    isolated_config.with_name(isolated_config.name + ".tmp").symlink_to(victim)

    config.write_config({"email": "cook@example.com", "password": "must-not-escape"})

    assert victim.read_text() == "original contents"
    assert "must-not-escape" not in victim.read_text()
    assert not isolated_config.is_symlink()


def test_a_symlinked_config_path_is_refused_rather_than_followed(isolated_config, tmp_path):
    isolated_config.parent.mkdir(parents=True, exist_ok=True)
    victim = tmp_path / "elsewhere.json"
    victim.write_text("{}")
    isolated_config.symlink_to(victim)

    with pytest.raises(config.ConfigError) as excinfo:
        config.write_config({"email": "cook@example.com", "password": "must-not-escape"})

    assert "symbolic link" in str(excinfo.value)
    assert victim.read_text() == "{}"


def test_a_symlinked_config_is_never_reported_as_private(isolated_config, tmp_path):
    isolated_config.parent.mkdir(parents=True, exist_ok=True)
    victim = tmp_path / "elsewhere.json"
    victim.write_text("{}")
    victim.chmod(0o600)
    isolated_config.symlink_to(victim)

    assert config.file_is_private() is False


def test_an_existing_parent_directory_keeps_the_permissions_it_had(tmp_path, monkeypatch):
    """The proven defect: chmod 0700 on a directory the tool did not create."""
    shared = tmp_path / "somebody-elses-folder"
    shared.mkdir(mode=0o755)
    os.chmod(shared, 0o755)
    monkeypatch.setenv(config.CONFIG_ENV_VAR, str(shared / "config.json"))

    config.write_config({"email": "cook@example.com", "password": "hunter2"})

    assert stat.S_IMODE(shared.stat().st_mode) == 0o755, "an existing folder is not ours to lock"
    assert stat.S_IMODE((shared / "config.json").stat().st_mode) == 0o600
    assert config.parent_is_private() is False


def test_a_folder_the_tool_creates_is_closed_to_other_accounts(tmp_path, monkeypatch):
    target = tmp_path / "fresh" / "config.json"
    monkeypatch.setenv(config.CONFIG_ENV_VAR, str(target))

    config.write_config({"email": "cook@example.com", "password": "hunter2"})

    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700
    assert config.parent_is_private() is True


def test_a_failed_write_leaves_no_temp_file_holding_the_password(isolated_config, monkeypatch):
    isolated_config.parent.mkdir(parents=True, exist_ok=True)

    def explode(*args, **kwargs):
        raise OSError("No space left on device")

    monkeypatch.setattr(config.os, "replace", explode)
    with pytest.raises(OSError):
        config.write_config({"email": "cook@example.com", "password": "hunter2"})

    leftovers = list(isolated_config.parent.iterdir())
    assert leftovers == [], f"a temp file survived: {leftovers}"
