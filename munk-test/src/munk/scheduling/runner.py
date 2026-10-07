from __future__ import annotations

import logging
from threading import Event, Lock, Thread
from typing import Protocol

_logger = logging.getLogger(__name__)


class ScheduleExecutorLike(Protocol):
    def run_once(self) -> None: ...


class ScheduleRunner:
    def __init__(self, *, executor: ScheduleExecutorLike, poll_interval_sec: float = 1.0) -> None:
        self._executor = executor
        self._poll_interval_sec = poll_interval_sec
        self._stop_event = Event()
        self._lock = Lock()
        self._thread: Thread | None = None

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = Thread(target=self._run_loop, name="munk-schedule-runner", daemon=True)
            self._thread.start()

    def shutdown(self, *, wait_timeout_sec: float = 5.0) -> None:
        with self._lock:
            thread = self._thread
            self._stop_event.set()
        if thread is not None:
            thread.join(wait_timeout_sec)

    def run_once(self) -> None:
        self._executor.run_once()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._executor.run_once()
            except Exception:  # noqa: BLE001
                _logger.exception("schedule runner loop crashed")
            self._stop_event.wait(self._poll_interval_sec)
