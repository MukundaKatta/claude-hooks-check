"""Tests for the claude-hooks-check command-line interface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claude_hooks_check import __version__
from claude_hooks_check.cli import main


def _write(tmp_path: Path, name: str, data: object) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_main_clean_file_exit_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    p = _write(
        tmp_path,
        "settings.json",
        {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [{"type": "command", "command": "echo hi"}],
                    }
                ]
            }
        },
    )
    code = main([str(p)])
    out = capsys.readouterr().out
    assert code == 0
    assert "OK" in out
    assert "0 error(s)" in out


def test_main_error_file_exit_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    p = _write(
        tmp_path,
        "settings.json",
        {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "*",
                        "hooks": [{"type": "command", "command": "rm -rf /"}],
                    }
                ]
            }
        },
    )
    code = main([str(p)])
    out = capsys.readouterr().out
    assert code == 1
    assert "E200" in out


def test_main_quiet_hides_warnings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A file whose only issue is a warning: in quiet mode nothing is printed and exit is 0.
    p = _write(tmp_path, "settings.json", {"hooks": {}})
    code = main(["--quiet", str(p)])
    out = capsys.readouterr().out
    assert code == 0
    assert "W011" not in out
    assert out.strip() == ""


def test_main_quiet_shows_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    p = _write(
        tmp_path,
        "settings.json",
        {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "*",
                        "hooks": [{"type": "command", "command": "sudo rm x"}],
                    }
                ]
            }
        },
    )
    code = main(["--quiet", str(p)])
    out = capsys.readouterr().out
    assert code == 1
    assert "E200" in out


def test_main_multiple_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    good = _write(
        tmp_path,
        "good.json",
        {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo done"}]}]}},
    )
    bad = _write(tmp_path, "bad.json", {"hooks": {"PreToolUse": {"matcher": "*"}}})
    code = main([str(good), str(bad)])
    out = capsys.readouterr().out
    assert code == 1
    assert "2 file(s)" in out
    assert "E021" in out


def test_main_missing_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main([str(tmp_path / "does_not_exist.json")])
    out = capsys.readouterr().out
    assert code == 1
    assert "E000" in out


def test_main_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out
