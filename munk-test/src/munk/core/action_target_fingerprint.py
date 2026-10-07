from __future__ import annotations

from munk.core.action_target_models import TargetHandle


def handle_fingerprint(handle: TargetHandle | None) -> tuple[str, ...] | None:
    if handle is None:
        return None
    kind = str(handle.kind or "").strip().lower()
    if kind == "dom":
        return _dom_fingerprint(handle)
    if kind == "a11y":
        return _a11y_fingerprint(handle)
    return None


def _dom_fingerprint(handle: TargetHandle) -> tuple[str, ...] | None:
    if _has_text(handle.node_id):
        return ("dom", "node_id", str(handle.node_id).strip())
    if _has_text(handle.selector):
        return ("dom", "selector", str(handle.selector).strip())
    return None


def _a11y_fingerprint(handle: TargetHandle) -> tuple[str, ...] | None:
    # Prefer stable locator fields; ephemeral node_id is never an identity signal.
    if _has_text(handle.resource_id):
        return ("a11y", "resource_id", str(handle.resource_id).strip())
    if _has_text(handle.stable_key):
        return ("a11y", "stable_key", str(handle.stable_key).strip())
    return None


def _has_text(value: object | None) -> bool:
    return bool(str(value or "").strip())
