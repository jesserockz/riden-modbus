"""The Riden RD60xx model catalog: scaling profiles and limits.

Every RD60xx (and the rack-mount RK6006) shares one register map; the models
differ only in value scaling and output limits. The ID ranges and multipliers
follow the reference implementations (Baldanos ``rd6006``, ShayBox ``Riden``).

The RD6012P is special: its current scale depends on the selected current
range (register 20) — 0.1 mA resolution on the 6 A range, 1 mA on the 12 A
range — so resolving its profile needs the probed ``current_range``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scaling:
    """Value scales (multipliers applied to raw register words)."""

    voltage: float
    current: float
    power: float


@dataclass(frozen=True)
class ModelProfile:
    """One model's name, scaling and output limits."""

    name: str
    scaling: Scaling
    max_voltage: float
    max_current: float


_STANDARD = Scaling(voltage=0.01, current=0.01, power=0.01)
_MILLIAMP = Scaling(voltage=0.01, current=0.001, power=0.01)
_PRECISION = Scaling(voltage=0.001, current=0.0001, power=0.001)
_PRECISION_HIGH_RANGE = Scaling(voltage=0.001, current=0.001, power=0.001)

RD6006 = ModelProfile("RD6006", _MILLIAMP, max_voltage=60.0, max_current=6.0)
RD6006P = ModelProfile("RD6006P", _PRECISION, max_voltage=60.0, max_current=6.0)
RD6012 = ModelProfile("RD6012", _STANDARD, max_voltage=60.0, max_current=12.0)
RD6012P_LOW = ModelProfile("RD6012P", _PRECISION, max_voltage=60.0, max_current=6.0)
RD6012P_HIGH = ModelProfile(
    "RD6012P", _PRECISION_HIGH_RANGE, max_voltage=60.0, max_current=12.0
)
RD6018 = ModelProfile("RD6018", _STANDARD, max_voltage=60.0, max_current=18.0)
RD6024 = ModelProfile("RD6024", _STANDARD, max_voltage=60.0, max_current=24.0)
RK6006 = ModelProfile("RK6006", _MILLIAMP, max_voltage=60.0, max_current=6.0)


def profile_for(model: int, *, current_range: int = 0) -> ModelProfile:
    """Return the profile for a raw ID-register value (e.g. 60181).

    ``current_range`` is the value of register 20 and only matters for the
    RD6012P, whose current resolution follows the selected range.
    """
    if 60241 <= model <= 60249:
        return RD6024
    if 60180 <= model <= 60189:
        return RD6018
    if 60125 <= model <= 60129:
        return RD6012P_LOW if current_range == 0 else RD6012P_HIGH
    if 60120 <= model <= 60124:
        return RD6012
    if model == 60065:
        return RD6006P
    if model == 60066:
        return RK6006
    if 60060 <= model <= 60064:
        return RD6006
    raise ValueError(f"Unsupported Riden model ID: {model}")


def is_supported_model(model: int) -> bool:
    """Whether this library models the given raw ID-register value."""
    try:
        profile_for(model)
    except ValueError:
        return False
    return True


def model_name(model: int) -> str:
    """A user-facing model name, best-effort for unsupported IDs."""
    try:
        return profile_for(model).name
    except ValueError:
        return f"RD{model // 10}"
