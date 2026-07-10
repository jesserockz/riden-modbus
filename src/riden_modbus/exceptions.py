"""Exceptions raised by rd6018-modbus."""

from __future__ import annotations


class RidenValueValidationError(ValueError):
    """Raised when a value is outside its allowed domain."""
