"""A stored preset group (M0-M9)."""

from __future__ import annotations

from functools import cache

from .model import RidenComponent, gauge
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
    current: float | None
    over_voltage_protection: float | None
    over_current_protection: float | None

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
            writable=True,
            unit="V",
            min_value=0,
            max_value=profile.max_voltage,
            digits=2,
            maker_key="M_V",
            description="Preset output voltage",
        )

        current = gauge(
            81,
            scaling.current,
            signed=False,
            stride=4,
            writable=True,
            unit="A",
            min_value=0,
            max_value=profile.max_current,
            digits=2,
            maker_key="M_I",
            description="Preset output current limit",
        )

        over_voltage_protection = gauge(
            82,
            scaling.voltage,
            signed=False,
            stride=4,
            writable=True,
            unit="V",
            min_value=0,
            max_value=profile.max_voltage,
            digits=2,
            maker_key="M_OVP",
            description="Preset over-voltage protection",
        )

        over_current_protection = gauge(
            83,
            scaling.current,
            signed=False,
            stride=4,
            writable=True,
            unit="A",
            min_value=0,
            max_value=profile.max_current,
            digits=2,
            maker_key="M_OCP",
            description="Preset over-current protection",
        )

    return _Preset
