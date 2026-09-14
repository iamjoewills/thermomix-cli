"""A password must not escape through an error message, ever.

Anything can raise – a dependency, the network stack, a schema change at
Cookidoo. Whatever comes back out of the process has to be scrubbed first.
"""
from __future__ import annotations

import pytest

from thermomix_cli import cli, config

PASSWORD = "Zz-unlikely-password-42"


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv(config.CONFIG_ENV_VAR, str(tmp_path / "cfg" / "config.json"))
    monkeypatch.delenv("THERMOMIX_CLI_DEBUG", raising=False)
    config.register_secret(PASSWORD)


def explode(monkeypatch, exception):
    def boom():
        raise exception

    monkeypatch.setattr(cli, "app", boom)


def test_a_leaky_exception_is_scrubbed_before_it_is_printed(monkeypatch, capsys):
    explode(monkeypatch, RuntimeError(f"POST failed body=password={PASSWORD}"))

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    err = capsys.readouterr().err
    assert exit_info.value.code == 1
    assert PASSWORD not in err
    assert "********" in err


def test_the_ordinary_failure_is_one_readable_line_not_a_traceback(monkeypatch, capsys):
    explode(monkeypatch, RuntimeError("Cookidoo said no"))

    with pytest.raises(SystemExit):
        cli.main()

    err = capsys.readouterr().err
    assert "Cookidoo said no" in err
    assert "Traceback" not in err
    assert "THERMOMIX_CLI_DEBUG=1" in err


def test_the_debug_traceback_is_scrubbed_too(monkeypatch, capsys):
    monkeypatch.setenv("THERMOMIX_CLI_DEBUG", "1")
    explode(monkeypatch, RuntimeError(f"body=password={PASSWORD}"))

    with pytest.raises(SystemExit):
        cli.main()

    err = capsys.readouterr().err
    assert "Traceback" in err
    assert PASSWORD not in err


def test_a_missing_setup_exits_cleanly_with_advice(monkeypatch, capsys):
    explode(monkeypatch, config.ConfigError("No Cookidoo details saved yet.\nRun:  thermomix-cli setup"))

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    err = capsys.readouterr().err
    assert exit_info.value.code == 2
    assert "thermomix-cli setup" in err
    assert "Traceback" not in err


def test_interrupting_is_not_an_error_report(monkeypatch, capsys):
    explode(monkeypatch, KeyboardInterrupt())

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 130
    assert "Stopped." in capsys.readouterr().err


def test_a_normal_exit_code_is_passed_straight_through(monkeypatch):
    explode(monkeypatch, SystemExit(0))

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 0
