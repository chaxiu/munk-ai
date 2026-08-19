from __future__ import annotations

from mcp.server.fastmcp.utilities.types import Image
from mcp.types import CallToolResult, ContentBlock, TextContent

from munk.adapters.mcp.device_tool_outputs import SessionObserveOutput

__all__ = ["build_session_observe_call_tool_result"]


def build_session_observe_call_tool_result(output: SessionObserveOutput) -> CallToolResult:
    """Assemble MCP CallToolResult with structured observe JSON and optional ImageContent."""
    structured = output.model_dump(mode="json")
    content: list[ContentBlock] = [
        TextContent(type="text", text=output.model_dump_json()),
    ]
    screenshot_path = output.observation.screenshot_path
    if screenshot_path:
        content.append(
            Image(
                path=screenshot_path,
                format=_image_format_from_mime(output.observation.screenshot_mime_type),
            ).to_image_content()
        )
    return CallToolResult(
        content=content,
        structuredContent=structured,
    )


def _image_format_from_mime(mime_type: str | None) -> str | None:
    if not mime_type or "/" not in mime_type:
        return None
    subtype = mime_type.split("/", 1)[1].strip().lower()
    return subtype or None
