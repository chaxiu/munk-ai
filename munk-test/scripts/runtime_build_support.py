from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

BUILD_STATE_SCHEMA_VERSION = 1
RUNTIME_REQUIREMENTS_LOCK = "build/runtime-requirements.lock"


def requirements_lock_path(root_dir: Path) -> Path:
    return root_dir / RUNTIME_REQUIREMENTS_LOCK


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_build_state(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid build state payload: {path}")
    return payload


def write_build_state(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def build_state_payload(
    *,
    kind: str,
    pbs_release_tag: str,
    pbs_python_version: str,
    pbs_archive_flavor: str,
    pbs_target_triple: str,
    requirements_lock_path_value: Path,
    extra_inputs: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    lock_hash = sha256_file(requirements_lock_path_value)
    pbs = {
        "release_tag": pbs_release_tag,
        "python_version": pbs_python_version,
        "archive_flavor": pbs_archive_flavor,
        "target_triple": pbs_target_triple,
    }
    requirements_lock = {
        "path": str(requirements_lock_path_value),
        "sha256": lock_hash,
    }
    normalized_extra_inputs = dict(sorted((extra_inputs or {}).items()))
    requirements_fingerprint = _stable_fingerprint(
        {
            "pbs": pbs,
            "requirements_lock": requirements_lock,
        }
    )
    full_fingerprint = _stable_fingerprint(
        {
            "kind": kind,
            "pbs": pbs,
            "requirements_lock": requirements_lock,
            "extra_inputs": normalized_extra_inputs,
        }
    )
    return {
        "schema_version": BUILD_STATE_SCHEMA_VERSION,
        "kind": kind,
        "pbs": pbs,
        "requirements_lock": requirements_lock,
        "extra_inputs": normalized_extra_inputs,
        "requirements_fingerprint": requirements_fingerprint,
        "full_fingerprint": full_fingerprint,
    }


def same_requirements_state(current_state: Mapping[str, Any] | None, expected_state: Mapping[str, Any]) -> bool:
    if current_state is None:
        return False
    return current_state.get("requirements_fingerprint") == expected_state.get("requirements_fingerprint")


def same_full_state(current_state: Mapping[str, Any] | None, expected_state: Mapping[str, Any]) -> bool:
    if current_state is None:
        return False
    return current_state.get("full_fingerprint") == expected_state.get("full_fingerprint")


def same_pbs_runtime(current_state: Mapping[str, Any] | None, expected_state: Mapping[str, Any]) -> bool:
    if current_state is None:
        return False
    return current_state.get("pbs") == expected_state.get("pbs")


def _stable_fingerprint(payload: Mapping[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256_text(serialized)
