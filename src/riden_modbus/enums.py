"""Enumerations used across the RD6018 model."""

from __future__ import annotations

from enum import IntEnum


class ProtectionStatus(IntEnum):
    """Why the output tripped, if it did (register 16)."""

    NONE = 0
    OVER_VOLTAGE = 1
    OVER_CURRENT = 2


class OutputMode(IntEnum):
    """Whether the output is limited by voltage or current (register 17)."""

    CONSTANT_VOLTAGE = 0
    CONSTANT_CURRENT = 1


class Language(IntEnum):
    """Front-panel UI language (register 71)."""

    ENGLISH = 0
    CHINESE = 1
