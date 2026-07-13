"""riden-modbus — read and control Riden RD60xx power supplies over Modbus.

Probe the unit, construct ``RD60xx`` with the probed model, call
``await device.async_update()``, then read its sub-systems as normal Python
objects::

    probe = await RD60xx.async_probe(unit)
    device = RD60xx(unit, model=probe.model, current_range=probe.current_range)
    await device.async_update()

    device.output.voltage
    device.battery.charge
    device.presets[1].over_voltage_protection

The library is organized by sub-system — one file each for ``device_info``,
``output``, ``battery``, ``clock``, ``settings`` and ``preset`` — built on the
generic ``Component`` / ``RegisterField`` framework in
``modbus_connection.model``.
"""

from .battery import Battery
from .clock import Clock
from .device_info import DeviceInformation
from .enums import Language, OutputMode, ProtectionStatus
from .exceptions import RidenValueValidationError
from .models import (
    ModelProfile,
    Scaling,
    is_supported_model,
    model_name,
    profile_for,
)
from .output import Output
from .preset import Preset
from .rd60xx import RD60xx, RD60xxProbe
from .settings import Settings

__all__ = [
    "Battery",
    "Clock",
    "DeviceInformation",
    "Language",
    "ModelProfile",
    "Output",
    "OutputMode",
    "Preset",
    "ProtectionStatus",
    "RD60xx",
    "RD60xxProbe",
    "RidenValueValidationError",
    "Scaling",
    "Settings",
    "is_supported_model",
    "model_name",
    "profile_for",
]
