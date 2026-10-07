from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IOSDeviceBridgeSession:
    session_id: str
    base_url: str
    backend_kind: str
    device_udid: str


@dataclass(frozen=True)
class IOSDeviceBridgeDiagnosticsContext:
    operation_id: str | None = None
    run_dir: str | None = None
    attempt_index: int | None = None
    app_id: str | None = None
    plan_id: str | None = None
    case_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        values: dict[str, str | int | None] = {
            "operation_id": self.operation_id,
            "run_dir": self.run_dir,
            "attempt_index": self.attempt_index,
            "app_id": self.app_id,
            "plan_id": self.plan_id,
            "case_id": self.case_id,
        }
        return {
            key: value
            for key, value in values.items()
            if value is not None
        }


@dataclass(frozen=True)
class IOSBridgeRealDevice:
    udid: str
    name: str
    platform_version: str | None
    state: str | None
    backend_kind: str | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class IOSBridgeLaunchConfig:
    use_sudo: bool
    sudo_password: str | None = None


@dataclass(frozen=True)
class IOSBridgeStartupAttempt:
    port: int
    success: bool
    retryable: bool
    summary: str
    output_excerpt: str | None = None
    process: subprocess.Popen[str] | None = None
