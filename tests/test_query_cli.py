"""Tests for the script/query.py CLI (no real backend needed)."""

from __future__ import annotations

import importlib.util
import sys
from datetime import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from modbus_connection import ModbusConnectionError
from modbus_connection.mock import MockModbusConnection, MockModbusUnit

from riden_modbus import OutputMode, RD60xx

from .conftest import HOLDING

_SPEC = importlib.util.spec_from_file_location(
    "riden_query", Path(__file__).resolve().parents[1] / "script" / "query.py"
)
assert _SPEC and _SPEC.loader
query = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(query)


def _mock_connection() -> MockModbusConnection:
    connection = MockModbusConnection()
    connection.for_unit(1).holding.update(HOLDING)
    return connection


def test_format_values() -> None:
    assert query._format(None) == "—"
    assert query._format(OutputMode.CONSTANT_VOLTAGE) == "constant_voltage"
    assert query._format(time(14, 30)) == "14:30:00"
    assert query._format(21.5) == "21.5"


def test_parse_args_tcp() -> None:
    args = query._parse_args(["tcp", "1.2.3.4", "--unit", "7"])
    assert args.transport == "tcp"
    assert args.host == "1.2.3.4"
    assert args.unit == 7
    assert args.port == 502
    assert args.framer == "rtu"  # RTU-over-TCP default for serial gateways


def test_parse_args_serial() -> None:
    args = query._parse_args(["serial", "/dev/ttyUSB0"])
    assert args.transport == "serial"
    assert args.device == "/dev/ttyUSB0"
    assert args.unit == 1  # Riden station-address default
    assert args.baudrate == 115200  # Riden serial default


async def test_open_picks_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    """_open routes to the pymodbus backend matching the transport."""
    opened: list[tuple[str, Any]] = []

    async def connect_tcp(host: str, **kwargs: Any) -> str:
        opened.append((host, kwargs))
        return "tcp-connection"

    async def connect_serial(device: str, **kwargs: Any) -> str:
        opened.append((device, kwargs))
        return "serial-connection"

    monkeypatch.setattr("modbus_connection.pymodbus.connect_tcp", connect_tcp)
    monkeypatch.setattr("modbus_connection.pymodbus.connect_serial", connect_serial)

    args = query._parse_args(["tcp", "1.2.3.4", "--framer", "socket"])
    assert await query._open(args) == "tcp-connection"
    assert opened[-1] == ("1.2.3.4", {"port": 502, "framer": "socket"})

    args = query._parse_args(["serial", "/dev/ttyUSB0", "--baudrate", "9600"])
    assert await query._open(args) == "serial-connection"
    assert opened[-1] == (
        "/dev/ttyUSB0",
        {"baudrate": 9600, "parity": "N", "stopbits": 1, "bytesize": 8},
    )


def test_values_lists_every_subsystem_field(mock_modbus_unit: MockModbusUnit) -> None:
    """Each sub-system's public fields are enumerated, methods excluded."""
    device = RD60xx(mock_modbus_unit, model=60181)

    output_rows = query._values(device.output)
    output_names = {name for name, _value, _unit in output_rows}

    assert {
        "voltage_setpoint",
        "current_setpoint",
        "voltage",
        "current",
        "power",
        "input_voltage",
        "keypad_lock",
        "protection",
        "mode",
        "enabled",
        "active_preset",
        "current_range",
        "over_voltage_protection",
        "over_current_protection",
        "temperature",
    } <= output_names

    battery_rows = query._values(device.battery)
    battery_names = {name for name, _value, _unit in battery_rows}
    assert {"active", "voltage", "temperature", "charge", "energy"} <= battery_names

    # Methods / private helpers are not data rows.
    assert "set_voltage" not in output_names
    assert "async_update" not in output_names
    assert all(not name.startswith("_") for name in output_names)


def test_print_runs(
    capsys: pytest.CaptureFixture[str], mock_modbus_unit: MockModbusUnit
) -> None:
    device = RD60xx(mock_modbus_unit, model=60181)
    query._print(device)
    out = capsys.readouterr().out
    assert "Device" in out
    assert "Output" in out
    assert "Preset M0" in out
    assert "Preset M9" in out


async def test_run_queries_device(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    connection = _mock_connection()

    async def fake_open(args: object) -> MockModbusConnection:
        return connection

    monkeypatch.setattr(query, "_open", fake_open)

    assert await query._run(query._parse_args(["tcp", "1.2.3.4"])) == 0
    out = capsys.readouterr().out
    assert "RD6018" in out
    assert "2 Modbus reads" in out  # one probe read + one full-map read
    assert connection.connected is False  # closed afterwards


async def test_run_rejects_unsupported_model(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    connection = MockModbusConnection()
    connection.for_unit(1).holding[0] = 52051  # a DPS5205 is not an RD60xx

    async def fake_open(args: object) -> MockModbusConnection:
        return connection

    monkeypatch.setattr(query, "_open", fake_open)

    assert await query._run(query._parse_args(["tcp", "1.2.3.4"])) == 1
    assert "Unsupported model" in capsys.readouterr().err
    assert connection.connected is False  # still closed


async def test_run_reports_connect_error(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_open(args: object) -> MockModbusConnection:
        raise ModbusConnectionError("no route to host")

    monkeypatch.setattr(query, "_open", fake_open)

    assert await query._run(query._parse_args(["tcp", "1.2.3.4"])) == 1
    assert "Could not connect" in capsys.readouterr().err


async def test_run_reports_read_error(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    connection = MockModbusConnection()

    def boom() -> int:
        raise ModbusConnectionError("device gone")

    connection.for_unit(1).holding[0] = boom

    async def fake_open(args: object) -> MockModbusConnection:
        return connection

    monkeypatch.setattr(query, "_open", fake_open)

    assert await query._run(query._parse_args(["tcp", "1.2.3.4"])) == 1
    assert "Error reading device" in capsys.readouterr().err
    assert connection.connected is False  # still closed on failure


def test_main(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_open(args: object) -> MockModbusConnection:
        return _mock_connection()

    monkeypatch.setattr(query, "_open", fake_open)
    monkeypatch.setattr(sys, "argv", ["query.py", "tcp", "1.2.3.4"])

    assert query.main() == 0


def _async_return(value: object) -> Any:
    async def call(address: int, count: int) -> object:
        return value

    return call


async def test_counting_unit_counts_reads() -> None:
    inner = SimpleNamespace(
        read_input_registers=_async_return([1]),
        read_holding_registers=_async_return([2]),
        read_coils=_async_return([True]),
        read_discrete_inputs=_async_return([False]),
        unit_id=1,
    )
    counting = query._CountingUnit(inner)
    assert counting.unit_id == 1  # non-read attributes pass through
    assert await counting.read_input_registers(0, 1) == [1]
    assert await counting.read_holding_registers(0, 1) == [2]
    assert await counting.read_coils(0, 1) == [True]
    assert await counting.read_discrete_inputs(0, 1) == [False]
    assert counting.reads == 4
