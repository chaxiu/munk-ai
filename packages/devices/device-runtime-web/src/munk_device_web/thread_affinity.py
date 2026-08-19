from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from threading import Event, Lock, get_ident
from typing import TypeVar

T = TypeVar("T")

DEFAULT_AFFINITY_TIMEOUT_SEC = 120.0


class ThreadAffinityGate:
    """Serialize callables onto a single owner OS thread with reentrant inline calls."""

    def __init__(
        self,
        *,
        thread_name_prefix: str = "munk-web-device",
        default_timeout_sec: float = DEFAULT_AFFINITY_TIMEOUT_SEC,
    ) -> None:
        if default_timeout_sec <= 0:
            raise ValueError("default_timeout_sec must be > 0")
        self._default_timeout_sec = default_timeout_sec
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=thread_name_prefix)
        self._owner_ident: int | None = None
        self._owner_ready = Event()
        self._shutdown = False
        self._lock = Lock()
        future: Future[None] = self._executor.submit(self._capture_owner_ident)
        future.result()

    @property
    def shut_down(self) -> bool:
        return self._shutdown

    @property
    def owner_thread_ident(self) -> int:
        if not self._owner_ready.wait(timeout=5.0) or self._owner_ident is None:
            raise RuntimeError("thread affinity owner thread is not ready")
        return self._owner_ident

    def call(self, fn: Callable[[], T], *, timeout_sec: float | None = None) -> T:
        with self._lock:
            if self._shutdown:
                raise RuntimeError("thread affinity gate has been shut down")
        if self._owner_ident is not None and get_ident() == self._owner_ident:
            return fn()
        timeout = self._default_timeout_sec if timeout_sec is None else timeout_sec
        if timeout <= 0:
            raise ValueError("timeout_sec must be > 0")
        future: Future[T] = self._executor.submit(fn)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError as exc:
            raise RuntimeError(f"thread affinity call timed out after {timeout:g}s") from exc

    def shutdown(self) -> None:
        with self._lock:
            if self._shutdown:
                return
            self._shutdown = True
        self._executor.shutdown(wait=True, cancel_futures=False)

    def _capture_owner_ident(self) -> None:
        self._owner_ident = get_ident()
        self._owner_ready.set()
