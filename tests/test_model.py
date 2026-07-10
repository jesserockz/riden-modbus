"""Direct tests of the field-factory plumbing not reachable via device fields."""

from __future__ import annotations

import pytest

from riden_modbus import RidenValueValidationError
from riden_modbus.model import _number_validator, _with_number_validator, gauge


def test_writable_without_limits_stays_plain() -> None:
    """No limits means no validator is wrapped around the write."""
    field = gauge(0, 0.01, writable=True)
    assert field.writable is True


def test_custom_validator_is_kept() -> None:
    def validator(value: object) -> object:
        return value

    field = gauge(0, 0.01, writable=validator, min_value=0, max_value=10)
    assert field.writable is validator


def test_not_writable_ignores_limits() -> None:
    assert _with_number_validator(False, min_value=0, max_value=10) is False


def test_validator_with_single_bound() -> None:
    validate = _number_validator(max_value=5)
    assert validate(3) == 3  # no minimum to check
    with pytest.raises(RidenValueValidationError):
        validate(6)

    validate = _number_validator(min_value=5)
    assert validate(7) == 7  # no maximum to check
    with pytest.raises(RidenValueValidationError):
        validate(3)
