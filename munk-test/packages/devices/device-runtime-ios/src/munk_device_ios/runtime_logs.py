from __future__ import annotations

import logging
import shutil
import subprocess
import threading
from collections.abc import Callable
from typing import IO, Literal, Protocol, cast

from munk.device import RuntimeLogEntry, RuntimeLogLevel

logger = logging.getLogger(__name__)


class IOSLogStream(Protocol):
    def start(self) -> None: ...

    def drain(self) -> list[RuntimeLogEntry]: ...

    def stop(self) -> None: ...


ProcessFactory = Callable[[list[str]], subprocess.Popen[str]]
IOSLogDeviceKind = Literal["simulator", "real_device"]


class IOSRuntimeLogStream:
    def __init__(
        self,
        *,
        device_ref: str | None,
        bundle_id: str | None,
        device_kind: IOSLogDeviceKind | None = None,
        process_factory: ProcessFactory | None = None,
    ) -> None:
        self._device_ref = device_ref
        self._bundle_id = bundle_id
        self._device_kind = device_kind or _infer_device_kind(device_ref)
        stream_type = self._device_kind or "simulator"
        stream_cls: type[_BaseIOSRuntimeLogStream]
        if stream_type == "real_device":
            stream_cls = _RealDeviceIOSRuntimeLogStream
        else:
            stream_cls = _SimulatorIOSRuntimeLogStream
        self._stream: IOSLogStream = stream_cls(
            device_ref=device_ref,
            bundle_id=bundle_id,
            process_factory=process_factory or _default_process_factory,
        )

    def start(self) -> None:
        self._stream.start()

    def drain(self) -> list[RuntimeLogEntry]:
        return self._stream.drain()

    def stop(self) -> None:
        self._stream.stop()


class _BaseIOSRuntimeLogStream:
    def __init__(
        self,
        *,
        device_ref: str | None,
        bundle_id: str | None,
        process_factory: ProcessFactory,
    ) -> None:
        self._device_ref = device_ref
        self._bundle_id = bundle_id
        self._process_factory = process_factory
        self._process: subprocess.Popen[str] | None = None
        self._reader_thread: threading.Thread | None = None
        self._entries: list[RuntimeLogEntry] = []
        self._entries_lock = threading.Lock()
        self._disabled = False

    def start(self) -> None:
        if self._process is not None or self._disabled or not self._device_ref:
            return
        try:
            process = self._process_factory(self._build_command(self._device_ref))
        except (FileNotFoundError, subprocess.SubprocessError, OSError) as exc:
            self._disable(exc)
            return
        if process.stdout is None:
            try:
                process.kill()
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    return
            finally:
                self._disable(RuntimeError("iOS runtime log stream missing stdout pipe"))
            return
        self._process = process
        self._reader_thread = threading.Thread(
            target=self._pump_stdout,
            args=(process.stdout,),
            daemon=True,
            name=f"ios-runtime-logs-{self._stream_name}",
        )
        self._reader_thread.start()

    def drain(self) -> list[RuntimeLogEntry]:
        if self._disabled:
            return []
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

    @property
    def _stream_name(self) -> str:
        raise NotImplementedError

    def _build_command(self, _device_ref: str) -> list[str]:
        raise NotImplementedError

    def _disable(self, exc: Exception) -> None:
        logger.warning("ios_runtime_logs_disabled stream=%s device_ref=%s error=%s", self._stream_name, self._device_ref, exc)
        self._disabled = True
        self.stop()

    def _pump_stdout(self, stdout: IO[str]) -> None:
        try:
            for raw_line in stdout:
                entry = _parse_log_line(raw_line, bundle_id=self._bundle_id, device_kind=self._stream_name)
                if entry is None:
                    continue
                with self._entries_lock:
                    self._entries.append(entry)
        finally:
            try:
                stdout.close()
            except Exception:
                return


class _SimulatorIOSRuntimeLogStream(_BaseIOSRuntimeLogStream):
    @property
    def _stream_name(self) -> str:
        return "simulator"

    def _build_command(self, device_ref: str) -> list[str]:
        return _build_simulator_log_stream_command(device_ref)


class _RealDeviceIOSRuntimeLogStream(_BaseIOSRuntimeLogStream):
    @property
    def _stream_name(self) -> str:
        return "real_device"

    def _build_command(self, device_ref: str) -> list[str]:
        return _build_real_device_log_stream_command(device_ref)


def _infer_device_kind(device_ref: str | None) -> IOSLogDeviceKind | None:
    if not device_ref:
        return None
    if "-" in device_ref:
        return "simulator"
    return "real_device"


def _build_simulator_log_stream_command(device_ref: str) -> list[str]:
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


def _build_real_device_log_stream_command(device_ref: str) -> list[str]:
    # Real-device syslog collection is best-effort because libimobiledevice may be unavailable
    # even when CoreDevice transport is healthy on iOS 17+.
    idevicesyslog_path = shutil.which("idevicesyslog")
    if idevicesyslog_path is None:
        raise FileNotFoundError("idevicesyslog")
    return [idevicesyslog_path, "-u", device_ref]


def _default_process_factory(command: list[str]) -> subprocess.Popen[str]:
    return subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )


def _parse_log_line(
    raw_line: str,
    *,
    bundle_id: str | None,
    device_kind: str | None = None,
) -> RuntimeLogEntry | None:
    line = raw_line.strip()
    if not line:
        return None
    if bundle_id:
        normalized_line = line.casefold()
        tokens = {bundle_id.casefold()}
        bundle_tail = bundle_id.rsplit(".", 1)[-1]
        if bundle_tail:
            tokens.add(bundle_tail.casefold())
        if not any(token in normalized_line for token in tokens):
            return None
    return RuntimeLogEntry(
        timestamp_ms=None,
        level=_infer_log_level(line),
        source="ios_syslog",
        message=line,
        raw={"line": line, "device_kind": device_kind},
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
