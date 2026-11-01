import subprocess

import pytest
import typer
from typer.testing import CliRunner

from automations_cli.main import _run_script, app, is_playlist_url

runner = CliRunner()


def test_help_lists_top_level_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in (
        "generate-project",
        "organize-files",
        "subtitle",
        "gist",
        "download",
    ):
        assert command in result.stdout


def test_run_script_missing_script_exits_with_error() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        _run_script("definitely-not-a-real-script.py")
    assert exc_info.value.exit_code == 1


def test_run_script_propagates_child_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "call", lambda _command: 3)
    with pytest.raises(typer.Exit) as exc_info:
        _run_script("pg_backup_tool.py")
    assert exc_info.value.exit_code == 3


def test_run_script_maps_signal_death_to_shell_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subprocess, "call", lambda _command: -2)
    with pytest.raises(typer.Exit) as exc_info:
        _run_script("pg_backup_tool.py")
    assert exc_info.value.exit_code == 130


def test_is_playlist_url_returns_false_when_ytdlp_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_missing(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("yt-dlp")

    monkeypatch.setattr(subprocess, "run", raise_missing)
    assert is_playlist_url("https://example.com/watch?v=1") is False
