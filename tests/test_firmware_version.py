"""Tests for the script/firmware_version.py calver helper."""

from __future__ import annotations

import importlib.util
import runpy
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[1] / "script" / "firmware_version.py"
_SPEC = importlib.util.spec_from_file_location("riden_firmware_version", _PATH)
assert _SPEC and _SPEC.loader
firmware_version = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(firmware_version)

OCT_2026 = date(2026, 10, 12)


@pytest.mark.parametrize(
    ("previous", "today", "expected"),
    [
        # Nothing published yet.
        ("", OCT_2026, "26.10.1"),
        # The pre-calver semver version.
        ("1.0.0", OCT_2026, "26.10.1"),
        # Same month: continue the counter.
        ("26.10.1", OCT_2026, "26.10.2"),
        ("26.10.9", OCT_2026, "26.10.10"),
        (" 26.10.3\n", OCT_2026, "26.10.4"),
        # A new month or year restarts the counter.
        ("26.9.4", OCT_2026, "26.10.1"),
        ("25.10.4", OCT_2026, "26.10.1"),
        ("26.12.3", date(2027, 1, 5), "27.1.1"),
        # Months are not zero padded, so "26.1" must not match "26.10".
        ("26.1.5", OCT_2026, "26.10.1"),
        # Garbage is treated as nothing published.
        ("dev", OCT_2026, "26.10.1"),
        ("26.10.x", OCT_2026, "26.10.1"),
    ],
)
def test_next_version(previous: str, today: date, expected: str) -> None:
    assert firmware_version.next_version(previous, today) == expected


def test_main_with_explicit_date(capsys: pytest.CaptureFixture[str]) -> None:
    firmware_version.main(["--previous", "26.10.2", "--today", "2026-10-19"])
    assert capsys.readouterr().out == "26.10.3\n"


def test_main_defaults_to_today_utc(
    capsys: pytest.CaptureFixture[str],
) -> None:
    firmware_version.main([])
    today = datetime.now(UTC).date()
    assert capsys.readouterr().out == f"{today:%y}.{today.month}.1\n"


def test_runs_as_script(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys, "argv", [str(_PATH), "--previous", "", "--today", "2026-10-01"]
    )
    runpy.run_path(str(_PATH), run_name="__main__")
    assert capsys.readouterr().out == "26.10.1\n"
