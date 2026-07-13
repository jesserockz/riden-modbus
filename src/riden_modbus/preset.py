"""A stored preset group (M0-M9)."""

from __future__ import annotations

from functools import cache

from modbus_connection.model import gauge

from .model import RidenComponent, bounded
from .models import ModelProfile


class Preset(RidenComponent):
    """One preset group. Construct with ``index`` 1-10 for M0-M9.

    Each group is 4 consecutive registers starting at 80, so the fields carry a
    ``stride`` of 4. Group M0 holds the *active* setpoints and protection
    values: registers 80/81 mirror the live setpoint registers 8/9, and 82/83
    are the protection values the running output enforces.

    The field scales differ per model, so they live on the model-specific
    subclass built by :func:`preset_class`.
    """

    # Model-scaled fields, declared on the subclass preset_class() builds.
    voltage: float | None
    """Preset output voltage (V)."""

    current: float | None
    """Preset output current limit (A)."""

    over_voltage_protection: float | None
    """Preset over-voltage protection (V)."""

    over_current_protection: float | None
    """Preset over-current protection (A)."""

    @property
    def number(self) -> int:
        """The preset's M number (0-9)."""
        return self._index - 1


@cache
def preset_class(profile: ModelProfile) -> type[Preset]:
    """Build the :class:`Preset` subclass carrying a model's scaled fields."""
    scaling = profile.scaling

    class _Preset(Preset):
        voltage = gauge(
            80,
            scaling.voltage,
            signed=False,
            stride=4,
            unit="V",
            writable=bounded(0, profile.max_voltage),
        )

        current = gauge(
            81,
            scaling.current,
            signed=False,
            stride=4,
            unit="A",
            writable=bounded(0, profile.max_current),
        )

        over_voltage_protection = gauge(
            82,
            scaling.voltage,
            signed=False,
            stride=4,
            unit="V",
            writable=bounded(0, profile.max_voltage),
        )

        over_current_protection = gauge(
            83,
            scaling.current,
            signed=False,
            stride=4,
            unit="A",
            writable=bounded(0, profile.max_current),
        )

    return _Preset
