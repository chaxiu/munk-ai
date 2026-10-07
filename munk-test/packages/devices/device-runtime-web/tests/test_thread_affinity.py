from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from threading import get_ident

import pytest
from munk_device_web.thread_affinity import ThreadAffinityGate


def test_thread_affinity_gate_runs_on_owner_from_other_thread() -> None:
    gate = ThreadAffinityGate(thread_name_prefix="test-affinity")
    try:
        caller_ident = get_ident()
        owner_ident = gate.owner_thread_ident
        assert caller_ident != owner_ident

        def _probe() -> int:
            return get_ident()

        assert gate.call(_probe) == owner_ident
    finally:
        gate.shutdown()


def test_thread_affinity_gate_reentrant_on_owner_does_not_deadlock() -> None:
    gate = ThreadAffinityGate(thread_name_prefix="test-affinity-reentrant")
    try:

        def _nested() -> str:
            return gate.call(lambda: "inner")

        assert gate.call(_nested) == "inner"
    finally:
        gate.shutdown()


def test_thread_affinity_gate_rejects_calls_after_shutdown() -> None:
    gate = ThreadAffinityGate(thread_name_prefix="test-affinity-shutdown")
    gate.shutdown()
    gate.shutdown()

    with pytest.raises(RuntimeError, match="shut down"):
        gate.call(lambda: None)


def test_thread_affinity_gate_times_out() -> None:
    gate = ThreadAffinityGate(thread_name_prefix="test-affinity-timeout", default_timeout_sec=0.05)
    try:

        def _block() -> None:
            time.sleep(1.0)

        with pytest.raises(RuntimeError, match="timed out"):
            gate.call(_block)
    finally:
        gate.shutdown()


def test_thread_affinity_gate_serializes_across_callers() -> None:
    gate = ThreadAffinityGate(thread_name_prefix="test-affinity-serial")
    try:
        order: list[str] = []

        def _first() -> None:
            order.append("a-start")
            time.sleep(0.05)
            order.append("a-end")

        def _second() -> None:
            order.append("b-start")
            order.append("b-end")

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(gate.call, _first)
            time.sleep(0.01)
            second = pool.submit(gate.call, _second)
            first.result(timeout=2.0)
            second.result(timeout=2.0)

        assert order == ["a-start", "a-end", "b-start", "b-end"]
    finally:
        gate.shutdown()
