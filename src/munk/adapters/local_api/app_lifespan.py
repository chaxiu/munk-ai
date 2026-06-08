from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any

from munk.adapters.local_api.app_context import LocalApiAppContext

_logger = logging.getLogger(__name__)


def build_local_api_lifespan(
    *,
    context: LocalApiAppContext,
    orchestration_mcp_server: Any | None = None,
    device_mcp_server: Any | None = None,
):
    @asynccontextmanager
    async def lifespan(_app: Any) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            response = context.get_machine_service().cleanup_stale_claims()
            cleaned_count = int(response.payload["data"]["cleaned_count"])
            if cleaned_count > 0:
                _logger.info("cleaned %s stale device claims before serving", cleaned_count)
            if context.start_recording_bridge:
                bridge_manager = context.get_recording_service().bridge_manager
                bridge_manager.ensure_running()
                _logger.info("recording bridge ready at %s", bridge_manager.base_url)
            if orchestration_mcp_server is not None:
                await stack.enter_async_context(orchestration_mcp_server.session_manager.run())
            if device_mcp_server is not None:
                await stack.enter_async_context(device_mcp_server.session_manager.run())
            context.get_schedule_runner().start()
            try:
                yield
            finally:
                if context.schedule_runner is not None:
                    context.schedule_runner.shutdown()
                still_running = context.background_operation_supervisor.shutdown(
                    cancel_callback=context.request_background_cancel,
                )
                if still_running:
                    _logger.warning(
                        "local api shutdown leaving background operations running: %s",
                        ", ".join(still_running),
                    )
                if context.recording_service is not None:
                    context.recording_service.shutdown()

    return lifespan
