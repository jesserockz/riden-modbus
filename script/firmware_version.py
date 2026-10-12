#!/usr/bin/env python3
"""Compute the next calver version for the ESPHome bridge firmware.

Versions are ``YY.M.N``: the two-digit year, the month, and a release counter
that restarts at 1 every month (``26.10.1`` is the first release of October
2026). The counter continues from the version currently published, which the
firmware workflow reads from the deployed ``manifest.json``::

    python3 script/firmware_version.py --previous 26.10.1   # -> 26.10.2

Runs on the CI runner's system Python, so it uses only the standard library.
"""

from __future__ import annotations

import argparse
import re
from datetime import UTC, date, datetime

_CALVER = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def next_version(previous: str, today: date) -> str:
    """Return the version following ``previous`` for a release on ``today``.

    Anything that is not a calver version from the same month (an empty
    string, the old ``1.0.0`` semver, last month's release) starts a new
    month at 1.
    """
    prefix = f"{today:%y}.{today.month}"
    counter = 1
    match = _CALVER.fullmatch(previous.strip())
    if match and f"{match[1]}.{match[2]}" == prefix:
        counter = int(match[3]) + 1
    return f"{prefix}.{counter}"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--previous",
        default="",
        help="currently published version (empty when nothing is published)",
    )
    parser.add_argument(
        "--today",
        type=date.fromisoformat,
        default=None,
        help="release date as YYYY-MM-DD (default: today, UTC)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    today: date = args.today or datetime.now(UTC).date()
    print(next_version(args.previous, today))


if __name__ == "__main__":
    main()
