from __future__ import annotations

import io
import logging
import subprocess
import time

from munk_device_ios.runtime_logs import (
    IOSRuntimeLogStream,
    _build_real_device_log_stream_command,
    _build_simulator_log_stream_command,
    _parse_log_line,
)


class _FakeProcess:
    def __init__(self, stdout: io.StringIO | None = None, *, exited: bool = False) -> None:
        self.stdout = stdout
        self._exited = exited
        self.terminated = False
        self.killed = False
        self.wait_calls = 0

    def poll(self) -> int | None:
        return 0 if self._exited else None

    def terminate(self) -> None:
        self.terminated = True
        self._exited = True

    def kill(self) -> None:
        self.killed = True
        self._exited = True

    def wait(self, timeout: float | None = None) -> int:
        _ = timeout
        self.wait_calls += 1
        return 0


def _wait_for_entries(stream: IOSRuntimeLogStream, *, attempts: int = 20) -> list:
    for _ in range(attempts):
        entries = stream.drain()
        if entries:
            return entries
        time.sleep(0.01)
    return []


def test_build_simulator_log_stream_command_keeps_existing_shape() -> None:
    assert _build_simulator_log_stream_command("sim-udid") == [
        "xcrun",
        "simctl",
        "spawn",
        "sim-udid",
        "log",
        "stream",
        "--style",
        "compact",
        "--level",
        "debug",
    ]


def test_build_real_device_log_stream_command_uses_idevicesyslog(monkeypatch) -> None:
    monkeypatch.setattr("munk_device_ios.runtime_logs.shutil.which", lambda _name: "/opt/homebrew/bin/idevicesyslog")
    assert _build_real_device_log_stream_command("real-udid") == ["/opt/homebrew/bin/idevicesyslog", "-u", "real-udid"]


def test_runtime_log_stream_reads_simulator_logs() -> None:
    process = _FakeProcess(io.StringIO("info com.example.demo booted\nignored line\n"))
    captured_commands: list[list[str]] = []
    stream = IOSRuntimeLogStream(
        device_ref="4F6D6434-A7DD-4A66-9344-6C2E88578997",
        device_kind="simulator",
        bundle_id="com.example.demo",
        process_factory=lambda command: captured_commands.append(command) or process,
    )

    stream.start()
    entries = _wait_for_entries(stream)
    stream.stop()

    assert captured_commands == [_build_simulator_log_stream_command("4F6D6434-A7DD-4A66-9344-6C2E88578997")]
    assert [entry.message for entry in entries] == ["info com.example.demo booted"]
    assert entries[0].raw == {"line": "info com.example.demo booted", "device_kind": "simulator"}


def test_runtime_log_stream_reads_real_device_logs(monkeypatch) -> None:
    monkeypatch.setattr("munk_device_ios.runtime_logs.shutil.which", lambda _name: "/opt/homebrew/bin/idevicesyslog")
    process = _FakeProcess(io.StringIO("warning Demo foregrounded\n"))
    captured_commands: list[list[str]] = []
    stream = IOSRuntimeLogStream(
        device_ref="00008110ABCDEF1234567890ABCDEF12",
        device_kind="real_device",
        bundle_id="com.example.demo",
        process_factory=lambda command: captured_commands.append(command) or process,
    )

    stream.start()
    entries = _wait_for_entries(stream)
    stream.stop()

    assert captured_commands == [["/opt/homebrew/bin/idevicesyslog", "-u", "00008110ABCDEF1234567890ABCDEF12"]]
    assert [entry.level for entry in entries] == ["warning"]
    assert entries[0].raw == {"line": "warning Demo foregrounded", "device_kind": "real_device"}


def test_runtime_log_stream_downgrades_when_real_device_logging_command_is_missing(caplog) -> None:
    stream = IOSRuntimeLogStream(
        device_ref="00008110ABCDEF1234567890ABCDEF12",
        device_kind="real_device",
        bundle_id="com.example.demo",
        process_factory=lambda command: (_ for _ in ()).throw(FileNotFoundError(command[0])),
    )

    with caplog.at_level(logging.WARNING):
        stream.start()

    assert stream.drain() == []
    stream.stop()
    assert "ios_runtime_logs_disabled" in caplog.text
    assert "real_device" in caplog.text


def test_runtime_log_stream_downgrades_when_stdout_pipe_is_missing(caplog) -> None:
    process = _FakeProcess(stdout=None)
    stream = IOSRuntimeLogStream(
        device_ref="4F6D6434-A7DD-4A66-9344-6C2E88578997",
        device_kind="simulator",
        bundle_id="com.example.demo",
        process_factory=lambda command: process,
    )

    with caplog.at_level(logging.WARNING):
        stream.start()

    assert process.killed is True
    assert stream.drain() == []
    assert "missing stdout pipe" in caplog.text


def test_runtime_log_stream_stop_terminates_running_process() -> None:
    process = _FakeProcess(io.StringIO(""))
    stream = IOSRuntimeLogStream(
        device_ref="00008110ABCDEF1234567890ABCDEF12",
        device_kind="real_device",
        bundle_id="com.example.demo",
        process_factory=lambda command: process,
    )

    stream.start()
    stream.stop()
    stream.stop()

    assert process.terminated is True
    assert process.wait_calls == 1
    assert stream.drain() == []


def test_parse_log_line_filters_by_bundle_id_and_bundle_tail() -> None:
    assert _parse_log_line("info com.example.demo matched", bundle_id="com.example.demo") is not None
    entry = _parse_log_line("debug Demo matched", bundle_id="com.example.demo", device_kind="real_device")
    assert entry is not None
    assert entry.level == "debug"
    assert entry.raw == {"line": "debug Demo matched", "device_kind": "real_device"}
    assert _parse_log_line("warning unrelated process", bundle_id="com.example.demo") is None


def test_runtime_log_stream_downgrades_when_process_factory_raises_subprocess_error(caplog) -> None:
    def _raise_subprocess_error(command: list[str]) -> _FakeProcess:
        raise subprocess.SubprocessError("launch failed")

    stream = IOSRuntimeLogStream(
        device_ref="00008110ABCDEF1234567890ABCDEF12",
        device_kind="real_device",
        bundle_id="com.example.demo",
        process_factory=_raise_subprocess_error,
    )

    with caplog.at_level(logging.WARNING):
        stream.start()

    assert stream.drain() == []
    assert "launch failed" in caplog.text
