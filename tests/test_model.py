"""Direct tests of the local field helpers layered on modbus-connection."""

from __future__ import annotations

import pytest

from riden_modbus import RidenValueValidationError
from riden_modbus.model import bounded


def test_bounded_passes_in_range_values() -> None:
    validate = bounded(0, 10)
    assert validate(5) == 5
    assert validate(0) == 0
    assert validate(10) == 10


def test_bounded_with_single_bound() -> None:
    validate = bounded(max_value=5)
    assert validate(3) == 3  # no minimum to check
    with pytest.raises(RidenValueValidationError):
        validate(6)

    validate = bounded(min_value=5)
    assert validate(7) == 7  # no maximum to check
    with pytest.raises(RidenValueValidationError):
        validate(3)


def test_bounded_without_limits_accepts_anything() -> None:
    validate = bounded()
    assert validate(-1000) == -1000
    assert validate(1000) == 1000
