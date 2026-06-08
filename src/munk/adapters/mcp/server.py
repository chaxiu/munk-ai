from __future__ import annotations

import importlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from munk.adapters.mcp.tool_handlers import McpToolHandlers
from munk.adapters.mcp.tool_registry import register_mcp_tools
from munk.app_assets.service import AppAssetService
from munk.planning.storage import PlanStore
from munk.services.doctor_service import DoctorService
from munk.services.machine_command_service import MachineCommandService
from munk.services.operations.registry import OperationRegistry


def build_mcp_tools(*, client: Any) -> dict[str, Callable[..., Any]]:
    """Compatibility helpers for tests and stdio-style adapters built on Local API."""

    return {
        "plan": lambda payload, *, wait=True, detach=False: client.submit(  # noqa: ANN001
            path="/v1/plan",
            payload=payload,
            wait=wait,
            detach=detach,
        ),
        "run_plan": lambda payload, *, wait=True, detach=False: client.submit(  # noqa: ANN001
            path="/v1/run/plan",
            payload=payload,
            wait=wait,
            detach=detach,
        ),
        "review": lambda payload, *, wait=True, detach=False: client.review(  # noqa: ANN001
            payload=payload,
            wait=wait,
            detach=detach,
        ),
        "verify_change": lambda payload, *, wait=True, detach=False: client.submit(  # noqa: ANN001
            path="/v1/verify/change",
            payload=payload,
            wait=wait,
            detach=detach,
        ),
        "runs_get": lambda operation_id: client.get_operation(operation_id=operation_id),  # noqa: ANN001
        "runs_events": lambda operation_id, *, after_seq=0, limit=100: client.list_events(  # noqa: ANN001
            operation_id=operation_id,
            after_seq=after_seq,
            limit=limit,
        ),
        "runs_artifacts": lambda operation_id: client.get_artifacts(operation_id=operation_id),  # noqa: ANN001
        "runs_cancel": lambda operation_id: client.cancel(operation_id=operation_id),  # noqa: ANN001
        "runs_reproduce": lambda operation_id: client.reproduce(operation_id=operation_id),  # noqa: ANN001
    }


def create_mcp_server(
    *,
    machine_service_factory: Callable[[], MachineCommandService],
    doctor_service_factory: Callable[[], DoctorService] | None = None,
    app_service_factory: Callable[[], AppAssetService] | None = None,
    plan_store_factory: Callable[[], PlanStore] | None = None,
    operation_registry_factory: Callable[[], OperationRegistry] | None = None,
    workspace_root: Callable[[], Path] | None = None,
    handlers_factory: Callable[[], Any] | None = None,
    server_name: str = "Munk Handoff",
    instructions: str = (
        "Use Munk handoff tools for planning, review, verification, app and run inspection. "
        "Choose this endpoint for orchestration-style workflows, not step-by-step device control. "
        "Prefer structured tool arguments."
    ),
    streamable_http_path: str = "/mcp",
    register_tools: Callable[[Any, Any], None] = register_mcp_tools,
    host: str = "127.0.0.1",
    port: int = 16888,
) -> Any:
    FastMCP = getattr(importlib.import_module("mcp.server.fastmcp"), "FastMCP")
    TransportSecuritySettings = getattr(
        importlib.import_module("mcp.server.transport_security"),
        "TransportSecuritySettings",
    )
    handlers = (
        handlers_factory()
        if handlers_factory is not None
        else McpToolHandlers(
            machine_service_factory=machine_service_factory,
            doctor_service_factory=doctor_service_factory,
            app_service_factory=app_service_factory,
            plan_store_factory=plan_store_factory,
            operation_registry_factory=operation_registry_factory,
            workspace_root=workspace_root,
        )
    )
    allowed_hosts = [host, f"{host}:{port}"]
    if host == "127.0.0.1":
        allowed_hosts.extend(["localhost", f"localhost:{port}"])
    mcp = FastMCP(
        server_name,
        instructions=instructions,
        json_response=True,
        host=host,
        port=port,
        streamable_http_path=streamable_http_path,
        transport_security=TransportSecuritySettings(allowed_hosts=allowed_hosts),
    )
    register_tools(mcp, handlers)
    return mcp


def mount_mcp_http(app: FastAPI, *, mcp_server: Any) -> None:
    mcp_http_app = mcp_server.streamable_http_app()
    app.state.mcp_server = mcp_server
    for route in mcp_http_app.routes:
        app.router.routes.append(route)


def run_mcp_server() -> None:
    """Compatibility entrypoint for local stdio MCP usage."""
    service = MachineCommandService(workspace_root=Path.cwd(), entrypoint="mcp")
    create_mcp_server(
        machine_service_factory=lambda: service,
        host="127.0.0.1",
        port=16888,
    ).run(transport="stdio")
