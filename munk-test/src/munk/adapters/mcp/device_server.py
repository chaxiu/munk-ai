from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from munk.adapters.mcp.device_tool_handlers import DeviceMcpToolHandlers
from munk.adapters.mcp.device_tool_registry import register_device_mcp_tools
from munk.adapters.mcp.server import create_mcp_server
from munk.services.interactive import InteractiveService


def create_device_mcp_server(
    *,
    interactive_service_factory: Callable[[], InteractiveService],
    workspace_root: Callable[[], Path] | None = None,
    host: str = "127.0.0.1",
    port: int = 16888,
) -> Any:
    return create_mcp_server(
        workspace_root=workspace_root,
        handlers_factory=lambda: DeviceMcpToolHandlers(
            interactive_service_factory=interactive_service_factory,
            workspace_root=workspace_root,
        ),
        server_name="Munk Device Control",
        instructions=(
            "Device-control MCP for step-by-step observe/act (not plan/review/verify). "
            "Auto smoke: Host owns create/release via Local API /v1/interactive/sessions*; "
            "agents call session_observe / session_list_targets / session_act with that session_id. "
            "session_start / abort / finalize are debug-only."
        ),
        streamable_http_path="/mcp/device",
        register_tools=register_device_mcp_tools,
        host=host,
        port=port,
    )
