from __future__ import annotations

import os
import platform
import signal
import subprocess
from pathlib import Path
from time import monotonic, sleep
from typing import Any, cast
from uuid import uuid4

import httpx

from munk.config.load import load_resolved_config
from munk.runtime_distribution import resolve_runtime_layout
from .ios_device_bridge_models import (
    IOSBridgeLaunchConfig,
    IOSBridgeRealDevice,
    IOSBridgeStartupAttempt,
    IOSDeviceBridgeDiagnosticsContext,
    IOSDeviceBridgeSession,
)
from .ios_device_bridge_support import (
    allocate_ephemeral_port,
    consume_process_output,
    is_port_available,
)

DEFAULT_IOS_DEVICE_BRIDGE_HOST = "127.0.0.1"
DEFAULT_IOS_DEVICE_BRIDGE_PORT = 16910
DEFAULT_IOS_DEVICE_BRIDGE_STARTUP_TIMEOUT_SECONDS = 10.0
DEFAULT_IOS_DEVICE_BRIDGE_FALLBACK_RETRIES = 3

_default_manager: IOSDeviceBridgeManager | None = None


class IOSDeviceBridgeError(RuntimeError):
    """Raised when the local iOS device bridge cannot be started or contacted."""


class IOSDeviceBridgeManager:
    def __init__(
        self,
        *,
        project_root: Path,
        host: str = DEFAULT_IOS_DEVICE_BRIDGE_HOST,
        port: int = DEFAULT_IOS_DEVICE_BRIDGE_PORT,
        startup_timeout_seconds: float = DEFAULT_IOS_DEVICE_BRIDGE_STARTUP_TIMEOUT_SECONDS,
    ) -> None:
        self._project_root = project_root
        self._host = host
        self._preferred_port = port
        self._startup_timeout_seconds = startup_timeout_seconds
        self._process: subprocess.Popen[str] | None = None
        self._active_port: int | None = None
        self._manager_token = uuid4().hex
        self._last_startup_error_excerpt: str | None = None
        self._last_startup_attempts: list[str] = []

    @property
    def base_url(self) -> str:
        return f"http://{self._host}:{self._resolved_port()}"

    @property
    def active_port(self) -> int | None:
        return self._active_port

    @property
    def bridge_project_dir(self) -> Path:
        return self._project_root / "sidecars" / "ios-device-bridge"

    @property
    def bridge_runtime_dir(self) -> Path:
        layout = resolve_runtime_layout()
        if layout.layout_mode == "distribution" and layout.sidecars_root is not None:
            return layout.sidecars_root / "ios-device-bridge"
        return self.bridge_project_dir

    @property
    def dist_app_path(self) -> Path:
        return self.bridge_runtime_dir / "dist" / "app.js"

    @property
    def standalone_bootstrap_path(self) -> Path:
        return self.bridge_runtime_dir / "dist" / "standalone_bootstrap.js"

    @property
    def bundled_node_path(self) -> Path:
        layout = resolve_runtime_layout()
        if layout.sidecars_root is None:
            return Path("")
        manifest = getattr(layout, "manifest", None)
        if layout.layout_mode == "distribution" and manifest is not None:
            node_sidecar = manifest.sidecars.get("node")
            if node_sidecar is not None:
                return layout.runtime_root / node_sidecar.path
        node_executable = "node.exe" if platform.system() == "Windows" else "node"
        node_dir = layout.sidecars_root / "node"
        if node_executable == "node.exe":
            return node_dir / node_executable
        return node_dir / "bin" / node_executable

    def ensure_running(self) -> None:
        if self._process is not None and self._process.poll() is not None:
            self._last_startup_error_excerpt = self._consume_process_output(self._process)
            self._process = None
            self._active_port = None
        if self._process is not None and self._process.poll() is None and self.is_healthy():
            return
        if self._process is not None and self._process.poll() is None:
            self.shutdown()
        if not self.dist_app_path.exists():
            raise IOSDeviceBridgeError(
                f"ios device bridge build output missing: {self.dist_app_path}. Run `pnpm -r build` first."
            )
        if resolve_runtime_layout().layout_mode == "distribution" and not self.standalone_bootstrap_path.exists():
            raise IOSDeviceBridgeError(
                f"ios device bridge standalone bootstrap missing: {self.standalone_bootstrap_path}. "
                "Run `pnpm -r build` first."
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
                return
            if attempt.retryable:
                continue
            raise IOSDeviceBridgeError(self._build_start_error_message("ios device bridge failed to start"))
        self._process = None
        self._active_port = None
        raise IOSDeviceBridgeError(self._build_start_error_message("ios device bridge failed to start"))

    def shutdown(self) -> None:
        if self._process is None:
            self._active_port = None
            return
        self._terminate_process_group(self._process, signal.SIGTERM)
        try:
            self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._terminate_process_group(self._process, signal.SIGKILL)
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
                if response.status_code != 200:
                    return False
                payload = cast(object, response.json())
                if not isinstance(payload, dict):
                    return False
                payload_dict = cast(dict[str, object], payload)
                return payload_dict.get("managerToken") == self._manager_token
        except (httpx.HTTPError, ValueError):
            return False

    def create_session(
        self,
        *,
        device_udid: str,
        bundle_id: str,
        wda_bundle_id: str,
        platform_version: str | None,
        diagnostics: IOSDeviceBridgeDiagnosticsContext | None = None,
    ) -> IOSDeviceBridgeSession:
        self.ensure_running()
        payload: dict[str, Any] = {
            "device_udid": device_udid,
            "bundle_id": bundle_id,
            "wda_bundle_id": wda_bundle_id,
            "platform_version": platform_version,
        }
        if diagnostics is not None:
            payload["diagnostics"] = diagnostics.to_payload()
        with httpx.Client(timeout=10.0, trust_env=False) as client:
            response = client.post(f"{self.base_url}/sessions", json=payload)
            self._raise_for_bridge_error(response)
            data = response.json().get("data", {})
        return IOSDeviceBridgeSession(
            session_id=str(data["sessionId"]),
            base_url=self.base_url,
            backend_kind=str(data["backendKind"]),
            device_udid=str(data["deviceUdid"]),
        )

    def get_session_diagnostics(self, *, session_id: str) -> dict[str, Any]:
        if not self.is_healthy():
            raise IOSDeviceBridgeError("ios device bridge is not running")
        with httpx.Client(timeout=5.0, trust_env=False) as client:
            response = client.get(f"{self.base_url}/sessions/{session_id}/diagnostics")
            self._raise_for_bridge_error(response)
            payload = response.json()
        payload_dict = cast(dict[str, Any], payload) if isinstance(payload, dict) else {}
        data = payload_dict.get("data")
        if not isinstance(data, dict):
            raise IOSDeviceBridgeError("invalid bridge diagnostics payload")
        return cast(dict[str, Any], data)

    def list_real_devices(self) -> list[IOSBridgeRealDevice]:
        self.ensure_running()
        with httpx.Client(timeout=10.0, trust_env=False) as client:
            response = client.get(f"{self.base_url}/devices")
            self._raise_for_bridge_error(response)
            payload = response.json()
        payload_dict = cast(dict[str, Any], payload) if isinstance(payload, dict) else {}
        data = payload_dict.get("data", [])
        if not isinstance(data, list):
            raise IOSDeviceBridgeError("invalid bridge devices payload")
        devices: list[IOSBridgeRealDevice] = []
        for item in cast(list[Any], data):
            if not isinstance(item, dict):
                continue
            item_dict = cast(dict[str, Any], item)
            udid = item_dict.get("udid")
            name = item_dict.get("name")
            if not isinstance(udid, str) or not udid:
                continue
            if not isinstance(name, str) or not name:
                name = udid
            platform_version = item_dict.get("platform_version")
            state = item_dict.get("state")
            backend_kind = item_dict.get("backend_kind")
            devices.append(
                IOSBridgeRealDevice(
                    udid=udid,
                    name=name,
                    platform_version=platform_version if isinstance(platform_version, str) else None,
                    state=state if isinstance(state, str) else None,
                    backend_kind=backend_kind if isinstance(backend_kind, str) else None,
                    raw=item_dict,
                )
            )
        return devices

    def delete_session(self, *, session_id: str) -> None:
        if not self.is_healthy():
            return
        with httpx.Client(timeout=5.0, trust_env=False) as client:
            response = client.delete(f"{self.base_url}/sessions/{session_id}")
            if response.status_code not in {200, 204, 404}:
                self._raise_for_bridge_error(response)

    @staticmethod
    def _raise_for_bridge_error(response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        payload_dict = cast(dict[str, Any], payload) if isinstance(payload, dict) else {}
        error = payload_dict.get("error")
        if isinstance(error, dict):
            error_dict = cast(dict[str, Any], error)
            code = error_dict.get("code")
            message = error_dict.get("message")
            details = error_dict.get("details")
            detail_suffix = ""
            if details not in (None, "", {}, []):
                try:
                    detail_suffix = f" | details={details!r}"
                except Exception:  # noqa: BLE001
                    detail_suffix = " | details=<unprintable>"
            raise IOSDeviceBridgeError(f"{code}: {message}{detail_suffix}")
        message = response.text.strip() or f"ios device bridge request failed: {response.status_code}"
        raise IOSDeviceBridgeError(message)

    def _resolved_port(self) -> int:
        if self._active_port is None:
            raise IOSDeviceBridgeError("ios device bridge is not running")
        return self._active_port

    def _build_command(self) -> list[str]:
        layout = resolve_runtime_layout()
        if layout.layout_mode == "distribution":
            node_path = self.bundled_node_path
            if not node_path.exists():
                raise IOSDeviceBridgeError(f"bundled node runtime missing: {node_path}")
            return [str(node_path), str(self.standalone_bootstrap_path)]
        return [
            "pnpm",
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
            "$PORT",
            "dist/app.js",
        ]

    def _resolve_launch_config(self) -> IOSBridgeLaunchConfig:
        config = load_resolved_config(None, workspace_root=Path.cwd())
        bridge_config = config.ios_bridge if config is not None else None
        if bridge_config is None or not bridge_config.sudo_enabled:
            return IOSBridgeLaunchConfig(use_sudo=False)
        sudo_password = bridge_config.sudo_password.strip() if bridge_config.sudo_password is not None else ""
        if not sudo_password:
            raise IOSDeviceBridgeError("ios bridge sudo password is required when ios_bridge.sudo_enabled=true")
        return IOSBridgeLaunchConfig(use_sudo=True, sudo_password=sudo_password)

    def _wrap_command_with_sudo(self, command: list[str], *, child_env: dict[str, str]) -> list[str]:
        env_args = [
            f"HOST={child_env['HOST']}",
            f"PORT={child_env['PORT']}",
            f"NODE_ENV={child_env['NODE_ENV']}",
            f"MUNK_BRIDGE_MANAGER_TOKEN={child_env['MUNK_BRIDGE_MANAGER_TOKEN']}",
            f"MUNK_PARENT_PID={child_env['MUNK_PARENT_PID']}",
        ]
        return ["sudo", "-S", "-p", "", "--", "env", *env_args, *command]

    def _start_process(self, *, port: int) -> subprocess.Popen[str]:
        launch_config = self._resolve_launch_config()
        command = [part if part != "$PORT" else str(port) for part in self._build_command()]
        env = os.environ.copy()
        env["HOST"] = self._host
        env["PORT"] = str(port)
        env["MUNK_BRIDGE_MANAGER_TOKEN"] = self._manager_token
        env["MUNK_PARENT_PID"] = str(os.getpid())
        env["NODE_ENV"] = env.get("NODE_ENV", "development")
        if launch_config.use_sudo:
            command = self._wrap_command_with_sudo(command, child_env=env)
        process = subprocess.Popen(
            command,
            cwd=str(self.bridge_runtime_dir if resolve_runtime_layout().layout_mode == "distribution" else self._project_root),
            stdin=subprocess.PIPE if launch_config.use_sudo else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            start_new_session=True,
        )
        if launch_config.use_sudo:
            if process.stdin is None:
                process.kill()
                process.wait(timeout=2)
                raise IOSDeviceBridgeError("failed to open stdin for ios bridge sudo launch")
            process.stdin.write(f"{launch_config.sudo_password}\n")
            process.stdin.flush()
            process.stdin.close()
        return process

    def _startup_port_candidates(self) -> list[int]:
        ports = [self._preferred_port]
        ports.extend(self._allocate_ephemeral_port() for _ in range(DEFAULT_IOS_DEVICE_BRIDGE_FALLBACK_RETRIES))
        return ports

    def _attempt_start_on_port(self, port: int) -> IOSBridgeStartupAttempt:
        if port == self._preferred_port and not self._is_port_available(port):
            return IOSBridgeStartupAttempt(
                port=port,
                success=False,
                retryable=True,
                summary=f"port {port}: already occupied before launch",
            )
        process = self._start_process(port=port)
        deadline = monotonic() + self._startup_timeout_seconds
        while monotonic() < deadline:
            if process.poll() is not None:
                output_excerpt = self._consume_process_output(process)
                retryable = output_excerpt is not None and "EADDRINUSE" in output_excerpt
                return IOSBridgeStartupAttempt(
                    port=port,
                    success=False,
                    retryable=retryable,
                    summary=self._format_attempt_summary(
                        port=port,
                        reason="exited before becoming healthy",
                    ),
                    output_excerpt=output_excerpt,
                )
            if self.is_healthy(port=port):
                return IOSBridgeStartupAttempt(
                    port=port,
                    success=True,
                    retryable=False,
                    summary=f"port {port}: healthy",
                    process=process,
                )
            sleep(0.2)
        self._terminate_process_group(process, signal.SIGTERM)
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._terminate_process_group(process, signal.SIGKILL)
            process.wait(timeout=2)
        return IOSBridgeStartupAttempt(
            port=port,
            success=False,
            retryable=False,
            summary=self._format_attempt_summary(
                port=port,
                reason=f"failed to become healthy within {self._startup_timeout_seconds:.1f}s",
            ),
            output_excerpt=self._consume_process_output(process),
        )

    def _build_start_error_message(self, base_message: str) -> str:
        details: list[str] = [base_message, f"preferred port={self._preferred_port}"]
        if self._last_startup_attempts:
            attempts = "\n".join(f"- {attempt}" for attempt in self._last_startup_attempts)
            details.append(f"attempts:\n{attempts}")
        if self._last_startup_error_excerpt:
            details.append(f"bridge stderr/stdout:\n{self._last_startup_error_excerpt}")
        return ". ".join(details)

    def _format_attempt_summary(self, *, port: int, reason: str) -> str:
        return f"port {port}: {reason}; healthz={self._build_http_url(port=port)}/healthz"

    def _build_http_url(self, *, port: int) -> str:
        return f"http://{self._host}:{port}"

    def _is_port_available(self, port: int) -> bool:
        return is_port_available(host=self._host, port=port)

    def _allocate_ephemeral_port(self) -> int:
        return allocate_ephemeral_port(host=self._host)

    def _terminate_process_group(self, process: subprocess.Popen[str], sig: signal.Signals) -> None:
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            return
        except PermissionError:
            self._sudo_kill_process_group(process.pid, sig)

    def _sudo_kill_process_group(self, pgid: int, sig: signal.Signals) -> None:
        launch_config = self._resolve_launch_config()
        if not launch_config.use_sudo or not launch_config.sudo_password:
            raise PermissionError(f"permission denied killing ios bridge process group {pgid}")
        command = ["sudo", "-S", "-p", "", "--", "kill", f"-{sig.value}", f"-{pgid}"]
        killer = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if killer.stdin is not None:
            killer.stdin.write(f"{launch_config.sudo_password}\n")
            killer.stdin.flush()
            killer.stdin.close()
        killer.wait(timeout=5)

    def _bridge_process_error(self, fallback_message: str) -> str:
        if self._process is None or self._process.stderr is None:
            return fallback_message
        output = self._consume_process_output(self._process)
        if output:
            return f"{fallback_message}: {output}"
        return fallback_message

    @staticmethod
    def _consume_process_output(process: subprocess.Popen[str]) -> str | None:
        return consume_process_output(process)


def get_default_ios_device_bridge_manager() -> IOSDeviceBridgeManager:
    global _default_manager
    if _default_manager is None:
        layout = resolve_runtime_layout()
        _default_manager = IOSDeviceBridgeManager(project_root=layout.project_root)
    return _default_manager
