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
    current_setpoint: float | None
    voltage: float | None
    current: float | None
    power: float | None
    over_voltage_protection: float | None
    over_current_protection: float | None

    # Reported in centivolts on every model — the supplies take up to ~70 V in,
    # which could not fit a 16-bit word at the P models' millivolt scale.
    input_voltage = gauge(14, 0.01, signed=False, unit="V", digits=2, maker_key="V_IN")

    keypad_lock = boolean(
        15,
        writable=True,
        maker_key="KEYPAD",
        description="Front-panel keypad lock",
    )

    protection = enum(16, ProtectionStatus, maker_key="OVP_OCP")
    mode = enum(17, OutputMode, maker_key="CV_CC")

    enabled = boolean(
        18,
        writable=True,
        maker_key="OUTPUT",
        description="Output on/off",
    )

    active_preset = integer(
        19,
        signed=False,
        writable=True,
        min_value=0,
        max_value=9,
        digits=0,
        maker_key="PRESET",
        description="Recall preset group M0-M9",
    )

    # Only meaningful on the RD6012P (0 = 6 A range, 1 = 12 A range); a change
    # means the device needs re-probing, as the current scale follows it.
    current_range = integer(20, signed=False, maker_key="I_RANGE")

    # Sign lives in its own register: 0 = positive, 1 = negative.
    _temperature_sign = raw_register(4, maker_key="INT_C_S")
    _temperature_value = integer(5, signed=False, maker_key="INT_C")

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
            maker_key="V_SET",
            description="Output voltage setting",
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
            maker_key="I_SET",
            description="Output current limit setting",
        )

        voltage = gauge(
            10, scaling.voltage, signed=False, unit="V", digits=2, maker_key="V_OUT"
        )
        current = gauge(
            11, scaling.current, signed=False, unit="A", digits=2, maker_key="I_OUT"
        )

        # 32 bits: an RD6018 tops out at 1080 W, past a single word's range.
        power = uint32(12, scale=scaling.power, unit="W", digits=2, maker_key="P_OUT")

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
            maker_key="M0_OVP",
            description="Active over-voltage protection",
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
            maker_key="M0_OCP",
            description="Active over-current protection",
        )

    return _Output
