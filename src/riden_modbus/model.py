"""Riden-specific pieces layered on the ``modbus_connection.model`` framework."""

from __future__ import annotations

from collections.abc import Callable
from enum import IntEnum
from typing import Any

from modbus_connection.model import Component
from modbus_connection.model import (
    enum as _modbus_enum,
)
from modbus_connection.model import (
    gauge as _modbus_gauge,
)
from modbus_connection.model import (
    integer as _modbus_integer,
)
from modbus_connection.model import (
    raw_register as _modbus_raw_register,
)
from modbus_connection.model import (
    uint32 as _modbus_uint32,
)
from modbus_connection.model.fields import NumberField

from .exceptions import RidenValueValidationError
from .metadata import (
    BooleanMetadata,
    DatapointMetadata,
    EnumMetadata,
    NumberMetadata,
    OptionMetadata,
    attach_metadata,
    step_from_digits,
)
from .ranges import REGISTER_RANGES


def _number_validator(
    *,
    min_value: float | int | None = None,
    max_value: float | int | None = None,
) -> Callable[[Any], Any]:
    """Return a write validator for numeric Riden values."""

    def validate(value: Any) -> Any:
        number = float(value)

        if min_value is not None and number < min_value:
            raise RidenValueValidationError(
                f"Value {value} is below minimum {min_value}"
            )

        if max_value is not None and number > max_value:
            raise RidenValueValidationError(
                f"Value {value} is above maximum {max_value}"
            )

        return value

    return validate


def _with_number_validator(
    writable: bool | Callable[[Any], Any],
    *,
    min_value: float | int | None,
    max_value: float | int | None,
) -> bool | Callable[[Any], Any]:
    """Return writable or a validator-backed writable value."""
    if not writable:
        return False

    if callable(writable):
        return writable

    if min_value is None and max_value is None:
        return True

    return _number_validator(min_value=min_value, max_value=max_value)


def _number_metadata(
    *,
    min_value: float | int | None,
    max_value: float | int | None,
    step: float | int | None,
    digits: int | None,
    unit: str | None,
    writable: bool | Callable[[Any], Any],
) -> DatapointMetadata:
    return DatapointMetadata(
        value_kind="number",
        writable=bool(writable),
        number=NumberMetadata(
            min_value=min_value,
            max_value=max_value,
            step=step,
            digits=digits,
            unit=unit,
        ),
    )


def raw_register(
    address: int,
    *args: Any,
    writable: bool | Callable[[Any], Any] = False,
    **kwargs: Any,
):
    """Create a raw register field with Riden metadata."""
    field = _modbus_raw_register(
        address,
        *args,
        writable=writable,
        **kwargs,
    )

    return attach_metadata(
        field,
        DatapointMetadata(
            value_kind="raw",
            writable=bool(writable),
        ),
    )


def integer(
    address: int,
    *args: Any,
    min_value: float | int | None = None,
    max_value: float | int | None = None,
    step: float | int | None = None,
    digits: int | None = None,
    unit: str | None = None,
    writable: bool | Callable[[Any], Any] = False,
    **kwargs: Any,
):
    """Create an integer field with Riden metadata."""
    effective_step = step if step is not None else step_from_digits(digits)
    effective_writable = _with_number_validator(
        writable,
        min_value=min_value,
        max_value=max_value,
    )

    field = _modbus_integer(
        address,
        *args,
        writable=effective_writable,
        unit=unit,
        **kwargs,
    )

    return attach_metadata(
        field,
        _number_metadata(
            min_value=min_value,
            max_value=max_value,
            step=effective_step,
            digits=digits,
            unit=unit,
            writable=writable,
        ),
    )


def gauge(
    address: int,
    scale: float,
    *args: Any,
    min_value: float | int | None = None,
    max_value: float | int | None = None,
    step: float | int | None = None,
    digits: int | None = None,
    unit: str | None = None,
    writable: bool | Callable[[Any], Any] = False,
    **kwargs: Any,
):
    """Create a gauge field with Riden metadata."""
    effective_step = step if step is not None else step_from_digits(digits)
    effective_writable = _with_number_validator(
        writable,
        min_value=min_value,
        max_value=max_value,
    )

    field = _modbus_gauge(
        address,
        scale,
        *args,
        writable=effective_writable,
        unit=unit,
        **kwargs,
    )

    return attach_metadata(
        field,
        _number_metadata(
            min_value=min_value,
            max_value=max_value,
            step=effective_step,
            digits=digits,
            unit=unit,
            writable=writable,
        ),
    )


def uint32(
    address: int,
    *args: Any,
    digits: int | None = None,
    unit: str | None = None,
    **kwargs: Any,
):
    """Create a read-only 32-bit field with Riden metadata."""
    field = _modbus_uint32(
        address,
        *args,
        unit=unit,
        **kwargs,
    )

    return attach_metadata(
        field,
        _number_metadata(
            min_value=None,
            max_value=None,
            step=step_from_digits(digits),
            digits=digits,
            unit=unit,
            writable=False,
        ),
    )


def enum(
    address: int,
    enum_type: type[IntEnum],
    *args: Any,
    options: tuple[OptionMetadata, ...] | None = None,
    writable: bool | Callable[[Any], Any] = False,
    **kwargs: Any,
):
    """Create an enum field with Riden metadata."""
    field = _modbus_enum(
        address,
        enum_type,
        *args,
        writable=writable,
        **kwargs,
    )

    resolved_options = options or tuple(
        OptionMetadata(member.name.lower(), int(member), member.name)
        for member in enum_type
    )

    return attach_metadata(
        field,
        DatapointMetadata(
            value_kind="enum",
            writable=bool(writable),
            enum=EnumMetadata(enum_type=enum_type, options=resolved_options),
        ),
    )


class BooleanRegisterField(NumberField[bool]):
    """A 0/1 holding register exposed as ``bool | None``.

    The RD6018 has no coils — every on/off value is a holding register.
    """

    def decode(self, words: list[int], scale_exponent: int | None = None) -> Any:
        return bool(super().decode(words, scale_exponent))

    def encode(self, value: Any) -> list[int]:
        return super().encode(int(bool(value)))


def boolean(
    address: int,
    *,
    stride: int = 0,
    writable: bool = False,
    false_key: str = "off",
    true_key: str = "on",
    false_label: str | None = None,
    true_label: str | None = None,
):
    """Create a boolean register field with Riden metadata."""
    field = BooleanRegisterField(
        address,
        signed=False,
        stride=stride,
        writable=writable,
    )

    return attach_metadata(
        field,
        DatapointMetadata(
            value_kind="boolean",
            writable=writable,
            boolean=BooleanMetadata(
                false_key=false_key,
                true_key=true_key,
                false_label=false_label,
                true_label=true_label,
            ),
        ),
    )


class RidenComponent(Component):
    """An RD60xx sub-system constrained to the device's readable range."""

    register_ranges = REGISTER_RANGES

    def metadata_for(self, field: str) -> DatapointMetadata | None:
        """Return neutral Riden metadata for a field."""
        descriptor = self._register_fields.get(field)
        if descriptor is None:
            return None
        return getattr(descriptor, "riden_metadata", None)

    def require_metadata_for(self, field: str) -> DatapointMetadata:
        """Return Riden metadata for a field or raise."""
        metadata = self.metadata_for(field)
        if metadata is None:
            raise AttributeError(f"unknown or untyped Riden field {field!r}")
        return metadata

    async def async_write_datapoint(self, field: str, value: Any) -> None:
        """Write a Riden data point.

        This is the public write entry point for integrations. Unlike some
        Modbus devices the RD60xx needs no write-unlock sequence, so this
        delegates straight to the generic component write path.
        """
        await self.write(field, value)
