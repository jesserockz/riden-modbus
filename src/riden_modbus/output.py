"""The output channel: setpoints, live measurements, protection and state."""

from __future__ import annotations

from functools import cache

from .enums import OutputMode, ProtectionStatus
from .model import RidenComponent, boolean, enum, gauge, integer, raw_register, uint32
from .models import ModelProfile


class Output(RidenComponent):
    """Output control and measurements.

    The scale of the voltage/current/power fields differs per model, so they
    live on model-specific subclasses built by :func:`output_class`; this base
    holds the fields every model shares.
    """

    # Model-scaled fields, declared on the subclass output_class() builds.
    voltage_setpoint: float | None
    """Output voltage setting (V)."""

    current_setpoint: float | None
    """Output current limit setting (A)."""

    voltage: float | None
    """Measured output voltage (V)."""

    current: float | None
    """Measured output current (A)."""

    power: float | None
    """Measured output power (W)."""

    over_voltage_protection: float | None
    """Active over-voltage protection (V) — preset group M0's OVP."""

    over_current_protection: float | None
    """Active over-current protection (A) — preset group M0's OCP."""

    input_voltage = gauge(14, 0.01, signed=False, unit="V", digits=2)
    """Input voltage (V).

    Reported in centivolts on every model — the supplies take up to ~70 V in,
    which could not fit a 16-bit word at the P models' millivolt scale.
    """

    keypad_lock = boolean(15, writable=True)
    """Front-panel keypad lock."""

    protection = enum(16, ProtectionStatus)
    """Why the output tripped, if it did."""

    mode = enum(17, OutputMode)
    """Whether the output is limited by voltage or current."""

    enabled = boolean(18, writable=True)
    """Output on/off."""

    active_preset = integer(
        19, signed=False, writable=True, min_value=0, max_value=9, digits=0
    )
    """Writing recalls preset group M0-M9 into the active setpoints."""

    current_range = integer(20, signed=False)
    """Selected current range (0 = 6 A, 1 = 12 A).

    Only meaningful on the RD6012P; a change means the device needs
    re-probing, as the current scale follows it.
    """

    # Sign lives in its own register: 0 = positive, 1 = negative.
    _temperature_sign = raw_register(4)
    _temperature_value = integer(5, signed=False)

    @property
    def temperature(self) -> int | None:
        """Internal temperature (°C)."""
        sign = self._temperature_sign
        value = self._temperature_value
        if sign is None or value is None:
            return None
        return -value if sign else value

    async def set_voltage(self, volts: float) -> None:
        """Set the output voltage (V)."""
        await self.async_write_datapoint("voltage_setpoint", volts)

    async def set_current(self, amps: float) -> None:
        """Set the output current limit (A)."""
        await self.async_write_datapoint("current_setpoint", amps)

    async def set_enabled(self, enabled: bool) -> None:
        """Turn the output on or off."""
        await self.async_write_datapoint("enabled", enabled)


@cache
def output_class(profile: ModelProfile) -> type[Output]:
    """Build the :class:`Output` subclass carrying a model's scaled fields."""
    scaling = profile.scaling

    class _Output(Output):
        voltage_setpoint = gauge(
            8,
            scaling.voltage,
            signed=False,
            writable=True,
            unit="V",
            min_value=0,
            max_value=profile.max_voltage,
            digits=2,
        )

        current_setpoint = gauge(
            9,
            scaling.current,
            signed=False,
            writable=True,
            unit="A",
            min_value=0,
            max_value=profile.max_current,
            digits=2,
        )

        voltage = gauge(10, scaling.voltage, signed=False, unit="V", digits=2)
        current = gauge(11, scaling.current, signed=False, unit="A", digits=2)

        # 32 bits: an RD6018 tops out at 1080 W, past a single word's range.
        power = uint32(12, scale=scaling.power, unit="W", digits=2)

        # The active protection values are preset group M0 (registers 80-83).
        over_voltage_protection = gauge(
            82,
            scaling.voltage,
            signed=False,
            writable=True,
            unit="V",
            min_value=0,
            max_value=profile.max_voltage,
            digits=2,
        )

        over_current_protection = gauge(
            83,
            scaling.current,
            signed=False,
            writable=True,
            unit="A",
            min_value=0,
            max_value=profile.max_current,
            digits=2,
        )

    return _Output
