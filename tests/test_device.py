"""End-to-end tests of the object model over the in-memory mock backend."""

from __future__ import annotations

from datetime import datetime

import pytest
from modbus_connection.mock import MockModbusConnection, MockModbusUnit

from riden_modbus import (
    Language,
    OutputMode,
    ProtectionStatus,
    RD60xx,
    RidenValueValidationError,
)

from .conftest import HOLDING


class _CountingUnit:
    """Wraps a ModbusUnit and records read calls; delegates everything else."""

    def __init__(self, inner: MockModbusUnit) -> None:
        self._inner = inner
        self.register_blocks: list[tuple[int, int]] = []
        self.coil_blocks: list[tuple[int, int]] = []

    async def read_holding_registers(self, address: int, count: int) -> list[int]:
        self.register_blocks.append((address, count))
        return await self._inner.read_holding_registers(address, count)

    async def read_coils(self, address: int, count: int) -> list[bool]:
        self.coil_blocks.append((address, count))
        return await self._inner.read_coils(address, count)

    def __getattr__(self, name: str) -> object:
        return getattr(self._inner, name)


async def test_device_info(rd6018: RD60xx) -> None:
    await rd6018.async_update()
    info = rd6018.info
    assert info.manufacturer == "Riden"
    assert info.model == "RD6018"  # shaped inline by the property
    assert info.model_code == 6018
    assert info.serial_number == "12345678"
    assert info.firmware_version == "1.41"


async def test_device_info_empty_before_update(rd6018: RD60xx) -> None:
    info = rd6018.info
    assert info.model is None
    assert info.model_code is None
    assert info.serial_number is None
    assert info.firmware_version is None


async def test_output(rd6018: RD60xx) -> None:
    await rd6018.async_update()
    output = rd6018.output
    assert output.voltage_setpoint == pytest.approx(13.5)
    assert output.current_setpoint == pytest.approx(2.5)
    assert output.voltage == pytest.approx(13.48)
    assert output.current == pytest.approx(2.1)
    assert output.power == pytest.approx(900.0)  # 32-bit across registers 12-13
    assert output.input_voltage == pytest.approx(24.15)
    assert output.keypad_lock is True
    assert output.protection is ProtectionStatus.OVER_CURRENT
    assert output.mode is OutputMode.CONSTANT_CURRENT
    assert output.enabled is True
    assert output.active_preset == 3
    assert output.current_range == 0
    assert output.over_voltage_protection == pytest.approx(55.0)
    assert output.over_current_protection == pytest.approx(16.0)
    assert output.temperature == 32


async def test_negative_temperature(mock_modbus_unit: MockModbusUnit) -> None:
    """A set sign register (1) negates the separate value register."""
    mock_modbus_unit.holding.update({4: 1, 5: 12})
    device = RD60xx(mock_modbus_unit, model=60181)
    await device.output.async_update()
    assert device.output.temperature == -12


async def test_battery(rd6018: RD60xx) -> None:
    await rd6018.async_update()
    battery = rd6018.battery
    assert battery.active is True
    assert battery.voltage == pytest.approx(12.89)
    assert battery.temperature == -5  # signed via the sign register
    assert battery.charge == pytest.approx(100.0)
    assert battery.energy == pytest.approx(66.536)


async def test_clock(rd6018: RD60xx) -> None:
    await rd6018.async_update()
    assert rd6018.clock.datetime == datetime(2026, 7, 8, 14, 30, 45)


@pytest.mark.parametrize(
    ("register", "value"),
    [
        pytest.param(50, 32, id="invalid-day"),
        pytest.param(51, 25, id="invalid-hour"),
    ],
)
async def test_clock_invalid_values(
    rd6018: RD60xx, mock_modbus_unit: MockModbusUnit, register: int, value: int
) -> None:
    """Out-of-range clock words decode to None instead of raising."""
    mock_modbus_unit.holding[register] = value
    await rd6018.async_update()
    assert rd6018.clock.datetime is None


async def test_clock_empty_before_update(rd6018: RD60xx) -> None:
    assert rd6018.clock.date is None
    assert rd6018.clock.time is None
    assert rd6018.clock.datetime is None


async def test_settings(rd6018: RD60xx) -> None:
    await rd6018.async_update()
    settings = rd6018.settings
    assert settings.take_ok is True
    assert settings.take_out is False
    assert settings.boot_power is True
    assert settings.buzzer is True
    assert settings.logo is False
    assert settings.language is Language.ENGLISH
    assert settings.backlight == 4


async def test_presets(rd6018: RD60xx) -> None:
    await rd6018.async_update()

    m0 = rd6018.presets[0]
    assert m0.number == 0
    assert m0.voltage == rd6018.output.voltage_setpoint
    assert m0.over_voltage_protection == rd6018.output.over_voltage_protection

    m1 = rd6018.presets[1]
    assert m1.number == 1
    assert m1.voltage == pytest.approx(5.0)
    assert m1.current == pytest.approx(1.0)
    assert m1.over_current_protection == pytest.approx(12.0)

    m9 = rd6018.presets[9]
    assert m9.number == 9
    assert m9.voltage == pytest.approx(42.0)
    assert m9.current == pytest.approx(3.0)
    assert m9.over_voltage_protection == pytest.approx(45.0)
    assert m9.over_current_protection == pytest.approx(3.5)


async def test_full_update_is_a_single_read() -> None:
    """The whole map (0-119) pools into exactly one Modbus read, no coils."""
    inner = MockModbusConnection().for_unit(1)
    inner.holding.update(HOLDING)
    unit = _CountingUnit(inner)
    device = RD60xx(unit, model=60181)  # type: ignore[arg-type]

    await device.async_update()

    assert unit.register_blocks == [(0, 120)]
    assert unit.coil_blocks == []
    assert device.output.voltage == pytest.approx(13.48)
    assert device.presets[9].voltage == pytest.approx(42.0)


async def test_independent_component_update(rd6018: RD60xx) -> None:
    """A sub-system refreshes on its own, without the rest."""
    await rd6018.battery.async_update()
    assert rd6018.battery.voltage == pytest.approx(12.89)
    assert rd6018.battery.temperature == -5
    assert rd6018.output.voltage is None  # not updated yet
    assert rd6018.output.temperature is None


async def test_update_listener(rd6018: RD60xx) -> None:
    calls: list[int] = []
    unsubscribe = rd6018.output.add_update_listener(lambda: calls.append(1))
    await rd6018.output.async_update()
    await rd6018.output.async_update()
    assert len(calls) == 2
    unsubscribe()
    await rd6018.output.async_update()
    assert len(calls) == 2  # no longer notified


async def test_write_roundtrip(rd6018: RD60xx) -> None:
    await rd6018.async_update()
    await rd6018.output.set_voltage(5.05)
    await rd6018.output.set_current(1.5)
    await rd6018.output.set_enabled(False)
    await rd6018.output.async_write_datapoint("over_voltage_protection", 30.0)
    await rd6018.async_update()
    assert rd6018.output.voltage_setpoint == pytest.approx(5.05)
    assert rd6018.output.current_setpoint == pytest.approx(1.5)
    assert rd6018.output.enabled is False
    assert rd6018.output.over_voltage_protection == pytest.approx(30.0)
    assert rd6018.presets[0].over_voltage_protection == pytest.approx(30.0)


async def test_write_preset(rd6018: RD60xx) -> None:
    """A preset write lands on the strided M-group registers."""
    unit = rd6018.presets[1]._unit
    await rd6018.presets[1].async_write_datapoint("voltage", 9.0)
    assert (await unit.read_holding_registers(84, 1))[0] == 900


async def test_recall_preset(rd6018: RD60xx) -> None:
    unit = rd6018.output._unit
    await rd6018.async_recall_preset(7)
    assert (await unit.read_holding_registers(19, 1))[0] == 7


async def test_write_settings(rd6018: RD60xx) -> None:
    await rd6018.settings.async_write_datapoint("backlight", 2)
    await rd6018.settings.async_write_datapoint("language", Language.CHINESE)
    await rd6018.settings.async_write_datapoint("buzzer", False)
    await rd6018.settings.async_update()
    assert rd6018.settings.backlight == 2
    assert rd6018.settings.language is Language.CHINESE
    assert rd6018.settings.buzzer is False


async def test_set_clock(rd6018: RD60xx) -> None:
    """Setting the clock writes all six words in one block write."""
    await rd6018.clock.set_datetime(datetime(2026, 12, 31, 23, 59, 58))
    await rd6018.clock.async_update()
    assert rd6018.clock.datetime == datetime(2026, 12, 31, 23, 59, 58)


async def test_write_rejects_readonly(rd6018: RD60xx) -> None:
    with pytest.raises(AttributeError):
        await rd6018.output.write("voltage", 5.0)
    with pytest.raises(AttributeError):
        await rd6018.battery.write("charge", 0)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("voltage_setpoint", 70.0, id="voltage-above-max"),
        pytest.param("current_setpoint", -1.0, id="current-below-min"),
        pytest.param("active_preset", 10, id="preset-above-max"),
    ],
)
async def test_write_validation(rd6018: RD60xx, field: str, value: float) -> None:
    with pytest.raises(RidenValueValidationError):
        await rd6018.output.async_write_datapoint(field, value)


async def test_probe(rd6018: RD60xx) -> None:
    probe = await RD60xx.async_probe(rd6018.output._unit)
    assert probe.model == 60181
    assert probe.model_name == "RD6018"
    assert probe.serial_number == "12345678"
    assert probe.firmware_version == "1.41"
    assert probe.current_range == 0
    assert probe.is_supported is True


async def test_probe_unsupported_model(mock_modbus_unit: MockModbusUnit) -> None:
    mock_modbus_unit.holding[0] = 52051  # a DPS5205 is not an RD60xx
    probe = await RD60xx.async_probe(mock_modbus_unit)
    assert probe.model == 52051
    assert probe.model_name == "RD5205"  # best-effort fallback naming
    assert probe.is_supported is False


async def test_construct_unsupported_model(mock_modbus_unit: MockModbusUnit) -> None:
    with pytest.raises(ValueError, match="Unsupported Riden model ID"):
        RD60xx(mock_modbus_unit, model=52051)


async def test_metadata(rd6018: RD60xx) -> None:
    voltage = rd6018.output.require_metadata_for("voltage_setpoint")
    assert voltage.writable is True
    assert voltage.number is not None
    assert voltage.number.max_value == 60.0
    assert voltage.number.step == pytest.approx(0.01)
    assert voltage.number.unit == "V"

    current = rd6018.output.require_metadata_for("current_setpoint")
    assert current.number is not None
    assert current.number.max_value == 18.0  # RD6018 limit

    enabled = rd6018.output.require_metadata_for("enabled")
    assert enabled.value_kind == "boolean"
    assert enabled.boolean is not None
    assert enabled.boolean.true_key == "on"

    language = rd6018.settings.require_metadata_for("language")
    assert language.enum is not None
    assert {option.key for option in language.enum.options} == {"english", "chinese"}

    # Options fall back to the enum members when not given explicitly.
    protection = rd6018.output.require_metadata_for("protection")
    assert protection.enum is not None
    assert {option.key for option in protection.enum.options} == {
        "none",
        "over_voltage",
        "over_current",
    }

    backlight = rd6018.settings.require_metadata_for("backlight")
    assert backlight.number is not None
    assert backlight.number.step == 1  # digits=0

    sign = rd6018.output.metadata_for("_temperature_sign")
    assert sign is not None and sign.value_kind == "raw"

    assert rd6018.output.metadata_for("no_such_field") is None
    with pytest.raises(AttributeError):
        rd6018.output.require_metadata_for("no_such_field")
