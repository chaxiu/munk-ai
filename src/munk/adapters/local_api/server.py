from __future__ import annotations

import uvicorn

DEFAULT_LOCAL_API_HOST = "127.0.0.1"
DEFAULT_LOCAL_API_PORT = 16888


def serve_local_api(
    *,
    host: str = DEFAULT_LOCAL_API_HOST,
    port: int = DEFAULT_LOCAL_API_PORT,
    log_level: str = "info",
    enable_mcp: bool = True,
) -> None:
    from munk.adapters.local_api.app import create_local_api_app

    uvicorn.run(
        create_local_api_app(enable_mcp=enable_mcp, mcp_host=host, mcp_port=port),
        host=host,
        port=port,
        log_level=log_level,
    )
