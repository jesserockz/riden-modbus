"""Neutral Riden datapoint metadata.

This module intentionally contains no Home Assistant concepts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Literal

ValueKind = Literal["number", "enum", "boolean", "raw"]


@dataclass(frozen=True)
class NumberMetadata:
    """Metadata for numeric Riden values."""

    min_value: float | int | None = None
    max_value: float | int | None = None
    step: float | int | None = None
    digits: int | None = None
    unit: str | None = None


@dataclass(frozen=True)
class OptionMetadata:
    """Metadata for one discrete option."""

    key: str
    value: int
    label: str | None = None


@dataclass(frozen=True)
class EnumMetadata:
    """Metadata for selectable / discrete register values."""

    enum_type: type[IntEnum]
    options: tuple[OptionMetadata, ...]


@dataclass(frozen=True)
class BooleanMetadata:
    """Metadata for boolean register values."""

    false_key: str = "off"
    true_key: str = "on"
    false_label: str | None = None
    true_label: str | None = None


@dataclass(frozen=True)
class DatapointMetadata:
    """Neutral metadata for one Riden datapoint."""

    value_kind: ValueKind
    writable: bool = False
    number: NumberMetadata | None = None
    enum: EnumMetadata | None = None
    boolean: BooleanMetadata | None = None


def step_from_digits(digits: int | None) -> float | int | None:
    """Return the natural UI/write step from decimal precision."""
    if digits is None:
        return None

    if digits <= 0:
        return 1

    return 10**-digits


def attach_metadata(field: Any, metadata: DatapointMetadata) -> Any:
    """Attach Riden metadata to a modbus-connection field."""
    field.riden_metadata = metadata
    return field
