from __future__ import annotations

import logging
import os
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from time import monotonic, sleep
from typing import Any

import httpx

from munk.runtime_distribution import resolve_runtime_layout

DEFAULT_RECORDING_BRIDGE_HOST = "127.0.0.1"
DEFAULT_RECORDING_BRIDGE_PORT = 16900
DEFAULT_RECORDING_BRIDGE_STARTUP_TIMEOUT_SECONDS = 10.0
DEFAULT_RECORDING_BRIDGE_FALLBACK_RETRIES = 3
_logger = logging.getLogger(__name__)


class RecordingBridgeError(RuntimeError):
    """Raised when the local scrcpy bridge cannot be started or contacted."""


@dataclass(frozen=True)
class RecordingBridgeSession:
    recording_id: str
    base_url: str
    ws_url: str


@dataclass(frozen=True)
class RecordingBridgeStartupAttempt:
    port: int
    success: bool
    retryable: bool
    summary: str
    output_excerpt: str | None = None
    process: subprocess.Popen[str] | None = None


class RecordingBridgeManager:
    def __init__(
        self,
        *,
        project_root: Path,
        host: str = DEFAULT_RECORDING_BRIDGE_HOST,
        port: int = DEFAULT_RECORDING_BRIDGE_PORT,
        startup_timeout_seconds: float = DEFAULT_RECORDING_BRIDGE_STARTUP_TIMEOUT_SECONDS,
    ) -> None:
        self._project_root = project_root
        self._host = host
        self._preferred_port = port
        self._startup_timeout_seconds = startup_timeout_seconds
        self._process: subprocess.Popen[str] | None = None
        self._active_port: int | None = None
        self._last_startup_error_excerpt: str | None = None
        self._last_startup_attempts: list[str] = []

    @property
    def base_url(self) -> str:
        return self._build_http_url(port=self._resolved_port())

    @property
    def ws_base_url(self) -> str:
        return self._build_ws_url(port=self._resolved_port())

    @property
    def active_port(self) -> int | None:
        return self._active_port

    @property
    def bridge_project_dir(self) -> Path:
        return self._project_root / "sidecars" / "recording-bridge-local"

    @property
    def bridge_runtime_dir(self) -> Path:
        layout = resolve_runtime_layout()
        if layout.layout_mode == "distribution" and layout.sidecars_root is not None:
            return layout.sidecars_root / "recording-bridge"
        return self.bridge_project_dir

    @property
    def dist_app_path(self) -> Path:
        return self.bridge_runtime_dir / "dist" / "app.js"

    @property
    def fastify_cli_path(self) -> Path:
        return self.bridge_runtime_dir / "node_modules" / "fastify-cli" / "cli.js"

    @property
    def standalone_bootstrap_path(self) -> Path:
        return self.bridge_runtime_dir / "dist" / "standalone_bootstrap.js"

    @property
    def scrcpy_server_binary_path(self) -> Path:
        override = os.environ.get("MUNK_SCRCPY_SERVER_BINARY")
        if override:
            return Path(override)
        return self.bridge_runtime_dir / "node_modules" / "@yume-chan" / "fetch-scrcpy-server" / "server.bin"

    @property
    def bundled_node_path(self) -> Path:
        layout = resolve_runtime_layout()
        if layout.sidecars_root is None:
            return Path("")
        return layout.sidecars_root / "node" / "bin" / "node"

    def ensure_running(self) -> None:
        if self._process is not None and self._process.poll() is not None:
            self._last_startup_error_excerpt = self._consume_process_output(self._process)
            self._process = None
            self._active_port = None
        if self._process is not None and self._process.poll() is None and self.is_healthy():
            return
        if self._process is not None and self._process.poll() is None:
            _logger.warning("managed recording bridge became unhealthy; restarting sidecar")
            self.shutdown()
        if not self.dist_app_path.exists():
            raise RecordingBridgeError(
                f"recording bridge build output missing: {self.dist_app_path}. "
                "Run `pnpm -r build` first."
            )
        if resolve_runtime_layout().layout_mode == "distribution" and not self.standalone_bootstrap_path.exists():
            raise RecordingBridgeError(
                "recording bridge standalone bootstrap missing: "
                f"{self.standalone_bootstrap_path}. "
                "Run `pnpm -r build` first."
            )
        if not self.scrcpy_server_binary_path.exists():
            raise RecordingBridgeError(
                "recording bridge scrcpy-server binary missing: "
                f"{self.scrcpy_server_binary_path}. "
                "Run `pnpm --dir sidecars/recording-bridge-local exec fetch-scrcpy-server 3.3.3` first."
            )
        self._last_startup_error_excerpt = None
        self._last_startup_attempts = []
        for port in self._startup_port_candidates():
            attempt = self._attempt_start_on_port(port)
            self._last_startup_attempts.append(attempt.summary)
            if attempt.output_excerpt:
                self._last_startup_error_excerpt = attempt.output_excerpt
            if attempt.success:
                self._process = attempt.process
                self._active_port = port
                if port != self._preferred_port:
                    _logger.info(
                        "recording bridge preferred port %s unavailable; using fallback port %s",
                        self._preferred_port,
                        port,
                    )
                _logger.info("recording bridge started at %s", self.base_url)
                return
            if attempt.retryable:
                continue
            raise RecordingBridgeError(self._build_start_error_message("recording bridge failed to start"))
        self._process = None
        self._active_port = None
        raise RecordingBridgeError(self._build_start_error_message("recording bridge failed to start"))

    def shutdown(self) -> None:
        if self._process is None:
            self._active_port = None
            return
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=2)
        self._last_startup_error_excerpt = self._consume_process_output(self._process)
        self._process = None
        self._active_port = None

    def is_healthy(self, *, port: int | None = None) -> bool:
        resolved_port = port or self._active_port
        if resolved_port is None:
            return False
        try:
            with httpx.Client(timeout=1.0, trust_env=False) as client:
                response = client.get(f"{self._build_http_url(port=resolved_port)}/healthz")
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    def create_bridge_session(self, *, recording_id: str, device_ref: str | None = None) -> RecordingBridgeSession:
        self.ensure_running()
        payload: dict[str, Any] = {"recording_id": recording_id}
        if device_ref:
            payload["device_ref"] = device_ref
        with httpx.Client(timeout=10.0, trust_env=False) as client:
            create_response = client.post(f"{self.base_url}/sessions", json=payload)
            self._raise_for_bridge_error(create_response)
            start_response = client.post(f"{self.base_url}/sessions/{recording_id}/start")
            self._raise_for_bridge_error(start_response)
        return RecordingBridgeSession(
            recording_id=recording_id,
            base_url=self.base_url,
            ws_url=f"{self.ws_base_url}/sessions/{recording_id}/stream",
        )

    def stop_bridge_session(self, *, recording_id: str) -> None:
        if not self.is_healthy():
            return
        with httpx.Client(timeout=5.0, trust_env=False) as client:
            response = client.delete(f"{self.base_url}/sessions/{recording_id}")
            if response.status_code not in {200, 204, 404}:
                self._raise_for_bridge_error(response)

    @staticmethod
    def _raise_for_bridge_error(response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        message = response.text.strip() or f"recording bridge request failed: {response.status_code}"
        raise RecordingBridgeError(message)

    def _build_start_error_message(self, base_message: str) -> str:
        details: list[str] = [base_message, f"preferred port={self._preferred_port}"]
        if self._last_startup_attempts:
            attempts = "\n".join(f"- {attempt}" for attempt in self._last_startup_attempts)
            details.append(f"attempts:\n{attempts}")
        details.append(f"runtime assets: {self._runtime_asset_summary()}")
        if self._last_startup_error_excerpt:
            details.append(f"bridge stderr/stdout:\n{self._last_startup_error_excerpt}")
        return ". ".join(details)

    def _startup_port_candidates(self) -> list[int]:
        ports = [self._preferred_port]
        ports.extend(self._allocate_ephemeral_port() for _ in range(DEFAULT_RECORDING_BRIDGE_FALLBACK_RETRIES))
        return ports

    def _attempt_start_on_port(self, port: int) -> RecordingBridgeStartupAttempt:
        if port == self._preferred_port and not self._is_port_available(port):
            return RecordingBridgeStartupAttempt(
                port=port,
                success=False,
                retryable=True,
                summary=f"port {port}: already occupied before launch",
            )
        command = self._build_command(port=port)
        process = self._start_process(port, command=command)
        deadline = monotonic() + self._startup_timeout_seconds
        while monotonic() < deadline:
            if process.poll() is not None:
                output_excerpt = self._consume_process_output(process)
                retryable = output_excerpt is not None and "EADDRINUSE" in output_excerpt
                summary = "exited before becoming healthy"
                if retryable:
                    summary = "exited before becoming healthy (EADDRINUSE)"
                return RecordingBridgeStartupAttempt(
                    port=port,
                    success=False,
                    retryable=retryable,
                    summary=self._format_attempt_summary(
                        port=port,
                        reason=summary,
                        command=command,
                    ),
                    output_excerpt=output_excerpt,
                )
            if self.is_healthy(port=port):
                return RecordingBridgeStartupAttempt(
                    port=port,
                    success=True,
                    retryable=False,
                    summary=f"port {port}: healthy",
                    process=process,
                )
            sleep(0.2)
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        output_excerpt = self._consume_process_output(process)
        return RecordingBridgeStartupAttempt(
            port=port,
            success=False,
            retryable=False,
            summary=self._format_attempt_summary(
                port=port,
                reason=f"failed to become healthy within {self._startup_timeout_seconds:.1f}s",
                command=command,
            ),
            output_excerpt=output_excerpt,
        )

    def _start_process(self, port: int, *, command: list[str]) -> subprocess.Popen[str]:
        env = os.environ.copy()
        env["PORT"] = str(port)
        env["HOST"] = self._host
        env["NODE_ENV"] = env.get("NODE_ENV", "development")
        return subprocess.Popen(  # noqa: S603
            command,
            cwd=self.bridge_runtime_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _build_command(self, *, port: int) -> list[str]:
        layout = resolve_runtime_layout()
        if layout.layout_mode == "distribution":
            node_bin = str(self.bundled_node_path) if self.bundled_node_path.exists() else None
            if node_bin is None or not self.standalone_bootstrap_path.exists():
                raise RecordingBridgeError(
                    "recording bridge runtime assets missing; expected bundled node and standalone bootstrap"
                )
            return [
                node_bin,
                str(self.standalone_bootstrap_path),
            ]
        node_bin = shutil_which("node")
        pnpm_bin = shutil_which("pnpm")
        if node_bin is None or pnpm_bin is None:
            raise RecordingBridgeError("missing local Node.js or pnpm executable for recording bridge")
        return [
            pnpm_bin,
            "--dir",
            str(self.bridge_project_dir),
            "exec",
            "fastify",
            "start",
            "-l",
            "warn",
            "-a",
            self._host,
            "-p",
            str(port),
            "dist/app.js",
        ]

    def _format_attempt_summary(self, *, port: int, reason: str, command: list[str]) -> str:
        healthz_url = f"{self._build_http_url(port=port)}/healthz"
        command_text = " ".join(command)
        return (
            f"port {port}: {reason}; "
            f"healthz={healthz_url}; "
            f"cwd={self.bridge_runtime_dir}; "
            f"command={command_text}"
        )

    def _runtime_asset_summary(self) -> str:
        asset_pairs = [
            ("bridge_runtime_dir", self.bridge_runtime_dir),
            ("dist_app", self.dist_app_path),
            ("standalone_bootstrap", self.standalone_bootstrap_path),
            ("fastify_cli", self.fastify_cli_path),
            ("bundled_node", self.bundled_node_path),
            ("scrcpy_server", self.scrcpy_server_binary_path),
        ]
        parts: list[str] = []
        for label, path in asset_pairs:
            status = "exists" if path.exists() else "missing"
            parts.append(f"{label}={path} ({status})")
        return "; ".join(parts)

    def _resolved_port(self) -> int:
        return self._active_port or self._preferred_port

    def _build_http_url(self, *, port: int) -> str:
        return f"http://{self._host}:{port}"

    def _build_ws_url(self, *, port: int) -> str:
        return f"ws://{self._host}:{port}"

    def _is_port_available(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            return sock.connect_ex((self._host, port)) != 0

    def _allocate_ephemeral_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self._host, 0))
            return int(sock.getsockname()[1])

    @staticmethod
    def _consume_process_output(process: subprocess.Popen[str]) -> str | None:
        stdout = ""
        stderr = ""
        try:
            stdout, stderr = process.communicate(timeout=0.1)
        except subprocess.TimeoutExpired:
            _logger.debug("recording bridge output not fully available before timeout")
            return None
        combined = "\n".join(part.strip() for part in (stderr, stdout) if part and part.strip()).strip()
        return combined or None


def shutil_which(name: str) -> str | None:
    from shutil import which

    return which(name)
