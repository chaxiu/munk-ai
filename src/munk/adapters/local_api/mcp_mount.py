from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI

from munk.adapters.local_api.app_context import LocalApiAppContext
from munk.adapters.mcp.device_server import create_device_mcp_server
from munk.adapters.mcp.server import create_mcp_server, mount_mcp_http


@dataclass(frozen=True)
class LocalApiMcpServers:
    orchestration: Any | None
    device: Any | None


def build_local_api_mcp_servers(
    context: LocalApiAppContext,
    *,
    enable_mcp: bool,
    host: str,
    port: int,
) -> LocalApiMcpServers:
    if not enable_mcp:
        return LocalApiMcpServers(orchestration=None, device=None)
    return LocalApiMcpServers(
        orchestration=create_mcp_server(
            machine_service_factory=context.get_machine_service,
            host=host,
            port=port,
            workspace_root=lambda: context.workspace_root,
        ),
        device=create_device_mcp_server(
            interactive_service_factory=context.get_interactive_service,
            workspace_root=lambda: context.workspace_root,
            host=host,
            port=port,
        ),
    )


def mount_local_api_mcp(app: FastAPI, servers: LocalApiMcpServers) -> None:
    if servers.orchestration is not None:
        mount_mcp_http(app, mcp_server=servers.orchestration)
    if servers.device is not None:
        mount_mcp_http(app, mcp_server=servers.device)
