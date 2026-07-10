"""Readable RD60xx Modbus ranges.

The whole documented map (registers 0-119, including the M0-M9 preset groups)
sits in one contiguous readable span, so a full device refresh fits a single
Modbus read. The maintenance registers above it (``SYSTEM`` at 256 and the
bootloader trigger at 5633) are deliberately not modeled.
"""

from __future__ import annotations

REGISTER_RANGES: tuple[tuple[int, int], ...] = ((0, 119),)
