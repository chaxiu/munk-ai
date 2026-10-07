from __future__ import annotations

import time
from collections.abc import Callable

from .diffing import diff_settle_snapshot, strict_settle_profile
from .formatting import _build_settle_change, build_settle_summary
from .models import (
    PlatformSettleEnhancer,
    SettleComparableSnapshot,
    SettleDiff,
    SettleDiffFn,
    SettleProfile,
    SettleResult,
)


class GenericSettleStrategy:
    def __init__(
        self,
        *,
        poll_interval_sec: float,
        enhancer: PlatformSettleEnhancer | None = None,
        profile: SettleProfile | None = None,
        diff_fn: SettleDiffFn | None = None,
    ) -> None:
        self._poll_interval_sec = max(0.0, poll_interval_sec)
        self._enhancer = enhancer
        self._profile = profile or strict_settle_profile(diff_fn=diff_fn)

    @property
    def profile(self) -> SettleProfile:
        return self._profile

    def settle(
        self,
        *,
        before: SettleComparableSnapshot,
        capture: Callable[[], SettleComparableSnapshot],
        timeout_sec: float,
    ) -> SettleResult:
        started = time.monotonic()
        deadline = started + max(0.0, timeout_sec)
        attempts = 0
        baseline_diff = self._diff(before, before)
        changes: list[str] = []

        if _has_initial_timeout(deadline=deadline, poll_interval_sec=self._poll_interval_sec):
            return _build_timeout_result(
                started=started,
                attempts=attempts,
                final_snapshot=before,
                before_to_final=baseline_diff,
                status="timeout",
                changes=changes,
            )

        _sleep_until_next_poll(deadline=deadline, poll_interval_sec=self._poll_interval_sec)

        previous = capture()
        attempts += 1
        before_to_previous = self._diff(before, previous)
        changed_seen = before_to_previous.effective_changed
        initial_change = _build_settle_change(
            elapsed_sec=max(0.0, time.monotonic() - started),
            diff=before_to_previous,
        )
        if initial_change is not None:
            changes.append(initial_change)
        stable_rounds = 0

        while True:
            if time.monotonic() >= deadline:
                status = "changed_but_unstable" if changed_seen else "timeout"
                return _build_timeout_result(
                    started=started,
                    attempts=attempts,
                    final_snapshot=previous,
                    before_to_final=before_to_previous,
                    status=status,
                    changes=changes,
                )

            _sleep_until_next_poll(deadline=deadline, poll_interval_sec=self._poll_interval_sec)
            current = capture()
            attempts += 1

            previous_to_current = self._build_iteration_diff(
                before=before,
                previous=previous,
                current=current,
            )
            before_to_current = self._diff(before, current)
            changed_seen = changed_seen or before_to_current.effective_changed

            settle_change = _build_settle_change(
                elapsed_sec=max(0.0, time.monotonic() - started),
                diff=previous_to_current,
            )
            if settle_change is not None:
                changes.append(settle_change)

            stable_rounds = stable_rounds + 1 if not previous_to_current.effective_changed else 0
            if stable_rounds >= self._profile.stable_rounds:
                return _build_stable_result(
                    started=started,
                    attempts=attempts,
                    before_to_final=before_to_current,
                    previous_to_final=previous_to_current,
                    final_snapshot=current,
                    changed_seen=changed_seen,
                    changes=changes,
                )

            previous = current
            before_to_previous = before_to_current

    def _diff(
        self,
        previous: SettleComparableSnapshot,
        current: SettleComparableSnapshot,
    ) -> SettleDiff:
        return self._profile.diff_fn(previous, current)

    def _build_iteration_diff(
        self,
        *,
        before: SettleComparableSnapshot,
        previous: SettleComparableSnapshot,
        current: SettleComparableSnapshot,
    ) -> SettleDiff:
        default_diff = self._diff(previous, current)
        if self._enhancer is None:
            return default_diff
        enhanced = self._enhancer.enhance(before=before, previous=previous, current=current)
        if enhanced is not None and enhanced.changed:
            return enhanced
        return default_diff


def fixed_delay_settle(
    *,
    before: SettleComparableSnapshot,
    capture: Callable[[], SettleComparableSnapshot],
    delay_sec: float,
    diff_fn: SettleDiffFn | None = None,
) -> SettleResult:
    started = time.monotonic()
    wait_sec = max(0.0, delay_sec)
    if wait_sec > 0:
        time.sleep(wait_sec)
    final_snapshot = capture()
    before_to_final = (diff_fn or diff_settle_snapshot)(before, final_snapshot)
    elapsed_ms = int(round((time.monotonic() - started) * 1000.0))
    return SettleResult(
        status="delay_elapsed",
        timed_out=False,
        attempts=1,
        elapsed_ms=elapsed_ms,
        final_snapshot=final_snapshot,
        before_to_final=before_to_final,
        previous_to_final=None,
        summary=build_settle_summary("delay_elapsed", before_to_final, None, timed_out=False),
        changes=(),
    )


def _has_initial_timeout(*, deadline: float, poll_interval_sec: float) -> bool:
    return time.monotonic() >= deadline and poll_interval_sec > 0


def _sleep_until_next_poll(*, deadline: float, poll_interval_sec: float) -> None:
    wait_sec = min(poll_interval_sec, max(0.0, deadline - time.monotonic()))
    if wait_sec > 0:
        time.sleep(wait_sec)


def _build_timeout_result(
    *,
    started: float,
    attempts: int,
    final_snapshot: SettleComparableSnapshot,
    before_to_final: SettleDiff,
    status: str,
    changes: list[str],
) -> SettleResult:
    elapsed_ms = int(round((time.monotonic() - started) * 1000.0))
    return SettleResult(
        status=status,
        timed_out=True,
        attempts=attempts,
        elapsed_ms=elapsed_ms,
        final_snapshot=final_snapshot,
        before_to_final=before_to_final,
        previous_to_final=None,
        summary=build_settle_summary(status, before_to_final, None, timed_out=True),
        changes=tuple(changes),
    )


def _build_stable_result(
    *,
    started: float,
    attempts: int,
    before_to_final: SettleDiff,
    previous_to_final: SettleDiff,
    final_snapshot: SettleComparableSnapshot,
    changed_seen: bool,
    changes: list[str],
) -> SettleResult:
    status = "changed_and_stable" if changed_seen else "no_visible_change"
    elapsed_ms = int(round((time.monotonic() - started) * 1000.0))
    return SettleResult(
        status=status,
        timed_out=False,
        attempts=attempts,
        elapsed_ms=elapsed_ms,
        final_snapshot=final_snapshot,
        before_to_final=before_to_final,
        previous_to_final=previous_to_final,
        summary=build_settle_summary(status, before_to_final, previous_to_final, timed_out=False),
        changes=tuple(changes),
    )
