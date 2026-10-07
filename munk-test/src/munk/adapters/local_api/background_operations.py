from __future__ import annotations

import logging
import time
from collections.abc import Callable
from threading import Lock, Thread

_logger = logging.getLogger(__name__)

BackgroundOperationRunner = Callable[[], None]
CancelOperationCallback = Callable[[str], None]


class LocalBackgroundOperationSupervisor:
    def __init__(self) -> None:
        self._lock = Lock()
        self._threads: dict[str, Thread] = {}
        self._accepting_submissions = True

    def submit(self, operation_id: str, runner: BackgroundOperationRunner) -> None:
        with self._lock:
            if not self._accepting_submissions:
                raise RuntimeError("background operation supervisor is shutting down")
            if operation_id in self._threads:
                raise RuntimeError(f"background operation already exists: {operation_id}")
            thread = Thread(
                target=self._run_registered,
                args=(operation_id, runner),
                name=f"local-api-op-{operation_id}",
                daemon=True,
            )
            self._threads[operation_id] = thread
        thread.start()

    def active_operation_ids(self) -> list[str]:
        with self._lock:
            return list(self._threads.keys())

    def shutdown(
        self,
        *,
        cancel_callback: CancelOperationCallback,
        wait_timeout_sec: float = 5.0,
    ) -> list[str]:
        with self._lock:
            self._accepting_submissions = False
            items = list(self._threads.items())
        operation_ids = [operation_id for operation_id, _thread in items]
        for operation_id in operation_ids:
            try:
                cancel_callback(operation_id)
            except Exception:  # noqa: BLE001
                _logger.exception("failed to request cancel for background operation %s", operation_id)
        deadline = time.monotonic() + wait_timeout_sec
        for _operation_id, thread in items:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            thread.join(remaining)
        still_running = [operation_id for operation_id, thread in items if thread.is_alive()]
        if still_running:
            _logger.warning(
                "background operations still running after shutdown wait: %s",
                ", ".join(still_running),
            )
        return still_running

    def _run_registered(self, operation_id: str, runner: BackgroundOperationRunner) -> None:
        try:
            runner()
        except Exception:  # noqa: BLE001
            _logger.exception("background operation crashed: %s", operation_id)
        finally:
            with self._lock:
                self._threads.pop(operation_id, None)
