from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any

from munk.adapters.local_api.app_context import LocalApiAppContext
from munk.services.ios import get_default_ios_device_bridge_manager
from munk.services.operations.payload_migration import migrate_operations_payloads

_logger = logging.getLogger(__name__)


def _migrate_operation_payloads_on_startup() -> None:
    try:
        migration = migrate_operations_payloads()
    except Exception:
        _logger.exception("failed to migrate operation payloads before serving")
        return
    if migration.operations_externalized or migration.events_externalized:
        _logger.info(
            "externalized operation payloads operations=%s events=%s",
            migration.operations_externalized,
            migration.events_externalized,
        )


def build_local_api_lifespan(
    *,
    context: LocalApiAppContext,
    orchestration_mcp_server: Any | None = None,
    device_mcp_server: Any | None = None,
):
    @asynccontextmanager
    async def lifespan(_app: Any) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            _migrate_operation_payloads_on_startup()
            response = context.get_machine_service().cleanup_stale_claims()
            cleaned_count = int(response.payload["data"]["cleaned_count"])
            reconciled_count = int(response.payload["data"].get("reconciled_count") or 0)
            if cleaned_count > 0:
                _logger.info("cleaned %s stale device claims before serving", cleaned_count)
            if reconciled_count > 0:
                _logger.info("reconciled %s orphaned operations before serving", reconciled_count)
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
                get_default_ios_device_bridge_manager().shutdown()

    return lifespan
