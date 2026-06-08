from __future__ import annotations

import subprocess
import threading
from collections.abc import Callable
from typing import IO, Protocol, cast

from munk.device import RuntimeLogEntry, RuntimeLogLevel


class IOSLogStream(Protocol):
    def start(self) -> None: ...

    def drain(self) -> list[RuntimeLogEntry]: ...

    def stop(self) -> None: ...


ProcessFactory = Callable[[list[str]], subprocess.Popen[str]]


class IOSRuntimeLogStream:
    def __init__(
        self,
        *,
        device_ref: str | None,
        bundle_id: str | None,
        process_factory: ProcessFactory | None = None,
    ) -> None:
        self._device_ref = device_ref
        self._bundle_id = bundle_id
        self._process_factory = process_factory or _default_process_factory
        self._process: subprocess.Popen[str] | None = None
        self._reader_thread: threading.Thread | None = None
        self._entries: list[RuntimeLogEntry] = []
        self._entries_lock = threading.Lock()

    def start(self) -> None:
        if self._process is not None or not self._device_ref:
            return
        process = self._process_factory(_build_log_stream_command(self._device_ref))
        if process.stdout is None:
            process.kill()
            process.wait(timeout=1.0)
            raise RuntimeError("iOS runtime log stream missing stdout pipe")
        self._process = process
        self._reader_thread = threading.Thread(
            target=self._pump_stdout,
            args=(process.stdout,),
            daemon=True,
            name="ios-runtime-logs",
        )
        self._reader_thread.start()

    def drain(self) -> list[RuntimeLogEntry]:
        with self._entries_lock:
            entries = list(self._entries)
            self._entries.clear()
            return entries

    def stop(self) -> None:
        process = self._process
        reader_thread = self._reader_thread
        self._process = None
        self._reader_thread = None
        try:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1.0)
        finally:
            if reader_thread is not None:
                reader_thread.join(timeout=1.0)
            with self._entries_lock:
                self._entries.clear()

    def _pump_stdout(self, stdout: IO[str]) -> None:
        try:
            for raw_line in stdout:
                entry = _parse_log_line(raw_line, bundle_id=self._bundle_id)
                if entry is None:
                    continue
                with self._entries_lock:
                    self._entries.append(entry)
        finally:
            try:
                stdout.close()
            except Exception:
                return


def _build_log_stream_command(device_ref: str) -> list[str]:
    return [
        "xcrun",
        "simctl",
        "spawn",
        device_ref,
        "log",
        "stream",
        "--style",
        "compact",
        "--level",
        "debug",
    ]


def _default_process_factory(command: list[str]) -> subprocess.Popen[str]:
    return subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )


def _parse_log_line(raw_line: str, *, bundle_id: str | None) -> RuntimeLogEntry | None:
    line = raw_line.strip()
    if not line:
        return None
    if bundle_id:
        tokens = {bundle_id}
        bundle_tail = bundle_id.rsplit(".", 1)[-1]
        if bundle_tail:
            tokens.add(bundle_tail)
        if not any(token in line for token in tokens):
            return None
    return RuntimeLogEntry(
        timestamp_ms=None,
        level=_infer_log_level(line),
        source="ios_syslog",
        message=line,
        raw={"line": line},
    )


def _infer_log_level(line: str) -> RuntimeLogLevel:
    lowered = line.lower()
    if " error " in lowered or lowered.startswith("error") or "<error>" in lowered:
        return cast(RuntimeLogLevel, "error")
    if " warning " in lowered or lowered.startswith("warning") or "<warning>" in lowered:
        return cast(RuntimeLogLevel, "warning")
    if " debug " in lowered or lowered.startswith("debug") or "<debug>" in lowered:
        return cast(RuntimeLogLevel, "debug")
    if " info " in lowered or lowered.startswith("info") or "<info>" in lowered:
        return cast(RuntimeLogLevel, "info")
    return cast(RuntimeLogLevel, "unknown")
