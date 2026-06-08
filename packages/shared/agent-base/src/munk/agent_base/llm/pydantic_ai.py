from __future__ import annotations

import asyncio
from contextvars import copy_context
from threading import Thread
from typing import Any


def run_agent_sync_compatible(agent: Any, /, *args: Any, **kwargs: Any) -> Any:
    """Run a pydantic-ai agent from sync code, even if an event loop already exists.

    `Agent.run_sync(...)` internally drives an event loop and raises
    `RuntimeError("This event loop is already running")` when called from a
    context that already owns one. For CLI/service code that remains synchronous,
    fall back to executing `agent.run(...)` inside a dedicated worker thread.
    """

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return agent.run_sync(*args, **kwargs)

    result: Any = None
    error: BaseException | None = None

    def _worker() -> None:
        nonlocal result, error
        try:
            result = asyncio.run(agent.run(*args, **kwargs))
        except BaseException as exc:  # noqa: BLE001
            error = exc

    context = copy_context()
    thread = Thread(target=lambda: context.run(_worker), name="pydantic-ai-sync-bridge", daemon=True)
    thread.start()
    thread.join()
    if error is not None:
        raise error
    return result
