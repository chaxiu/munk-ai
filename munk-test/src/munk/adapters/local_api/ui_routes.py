from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from munk.runtime_distribution import resolve_runtime_layout


def recording_ui_dist(*, project_root: Path) -> Path:
    layout = resolve_runtime_layout()
    if layout.layout_mode == "distribution":
        return layout.core_resources_root / "recording-ui"
    return project_root / "apps" / "web-ui" / "dist"


def recording_ui_index_response(*, dist_root: Path) -> FileResponse | JSONResponse:
    index_path = dist_root / "index.html"
    if not index_path.exists():
        build_hint = os.environ.get("MUNK_RECORDING_UI_BUILD_HINT", "pnpm -r build")
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "command": "recording_page",
                "error": {
                    "code": "recording_ui_unavailable",
                    "message": f"recording UI build output missing: {index_path}. Run `{build_hint}` first.",
                },
            },
        )
    return FileResponse(index_path)


def recording_ui_static_response(*, dist_root: Path, path: str) -> FileResponse | None:
    if not path:
        return None
    dist_root = dist_root.resolve()
    candidate = (dist_root / path).resolve()
    if candidate != dist_root and dist_root not in candidate.parents:
        return None
    if candidate.is_file():
        return FileResponse(candidate)
    return None


def build_ui_router(
    *,
    index_response_factory: Callable[[], FileResponse | JSONResponse],
    static_response_factory: Callable[[str], FileResponse | None],
) -> APIRouter:
    router = APIRouter()

    @router.get("/", include_in_schema=False)
    def recording_page():
        return index_response_factory()

    @router.get("/{path:path}", include_in_schema=False)
    def recording_page_path(path: str):
        static_response = static_response_factory(path)
        if static_response is not None:
            return static_response
        return index_response_factory()

    return router
