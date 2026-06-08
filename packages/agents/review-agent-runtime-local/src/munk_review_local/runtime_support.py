from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, cast
from uuid import uuid4

OPERATION_DIAGNOSTICS_SCHEMA_VERSION = "phase7e.operation_diagnostics.v1"
_MUNK_HOME_ENV = "MUNK_HOME"
_RUNTIME_ROOT_ENV = "MUNK_RUNTIME_ROOT"
_MANIFEST_NAME = "manifest.lock"


def default_runtime_root() -> Path:
    configured = os.environ.get(_RUNTIME_ROOT_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    manifest = _discover_manifest_from_executable()
    if manifest is not None:
        return manifest.parent
    return Path.cwd()


def create_unique_run_dir(*, prefix: str) -> Path:
    runs_dir = default_runs_root()
    runs_dir.mkdir(parents=True, exist_ok=True)
    for _attempt in range(8):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        suffix = uuid4().hex[:8]
        run_dir = runs_dir / f"{prefix}_{timestamp}_{suffix}"
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise RuntimeError(f"failed to allocate unique run directory for prefix '{prefix}'")


def default_runs_root() -> Path:
    munk_home = os.environ.get(_MUNK_HOME_ENV)
    if munk_home:
        return Path(munk_home).expanduser().resolve() / "runs"
    return default_runtime_root() / "runs"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def timer() -> float:
    return perf_counter()


def elapsed_ms(start_time: float) -> int:
    return max(0, int((perf_counter() - start_time) * 1000))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_operation_manifest(
    *,
    root_dir: Path,
    artifacts: dict[str, str],
    operation_id: str | None,
    operation_kind: str,
    schema_versions: dict[str, str],
) -> dict[str, Any]:
    return {
        "manifest_version": 2,
        "operation_id": operation_id,
        "operation_kind": operation_kind,
        "verification_verdict": None,
        "root_dir": str(root_dir),
        "primary_artifacts": _build_artifact_refs(artifacts=artifacts, scope="operation"),
        "case_runs": [],
        "reproduction": [],
        "schema_versions": dict(schema_versions),
        "upstream_review": None,
        "metadata": {},
    }


def refresh_manifest_artifact_exists(manifest: dict[str, Any]) -> dict[str, Any]:
    refreshed = dict(manifest)
    refreshed["primary_artifacts"] = {
        artifact_id: {
            **ref,
            "exists": Path(ref["path"]).exists(),
        }
        for artifact_id, ref in manifest.get("primary_artifacts", {}).items()
    }
    return refreshed


def build_json_artifact_check(
    *,
    artifact_id: str,
    path: Path,
    required_fields: tuple[str, ...] = (),
    expected_schema_version: str | None = None,
    required: bool = True,
) -> dict[str, Any]:
    if not path.exists():
        return {
            "artifact_id": artifact_id,
            "path": str(path),
            "required": required,
            "exists": False,
            "valid": False,
            "summary": "artifact not found",
        }

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {
            "artifact_id": artifact_id,
            "path": str(path),
            "required": required,
            "exists": True,
            "valid": False,
            "summary": f"invalid json: {exc}",
        }

    missing_fields = [field for field in required_fields if field not in payload]
    if missing_fields:
        return {
            "artifact_id": artifact_id,
            "path": str(path),
            "required": required,
            "exists": True,
            "valid": False,
            "summary": f"missing fields: {', '.join(missing_fields)}",
        }

    if expected_schema_version is not None and payload.get("schema_version") != expected_schema_version:
        return {
            "artifact_id": artifact_id,
            "path": str(path),
            "required": required,
            "exists": True,
            "valid": False,
            "summary": (
                "unexpected schema_version: "
                f"{payload.get('schema_version')!r} != {expected_schema_version!r}"
            ),
        }

    return {
        "artifact_id": artifact_id,
        "path": str(path),
        "required": required,
        "exists": True,
        "valid": True,
        "summary": "ok",
    }


def classify_exception(exc: Exception) -> str:
    text = f"{exc.__class__.__name__.lower()} {str(exc).lower()}"
    if "retrieval" in text or "embedding" in text or "sqlite-vec" in text:
        return "retrieval_error"
    if "artifact" in text or "manifest" in text:
        return "artifact_error"
    if "model" in text or "openai" in text or "gemini" in text or "config" in text:
        return "model_error"
    if isinstance(exc, ValueError):
        return "contract_error"
    if isinstance(exc, FileNotFoundError):
        return "artifact_error"
    return "unknown_error"


def resolve_provider_metadata(
    *,
    resolved_config: Any,
    role: str,
) -> tuple[str | None, str | None, dict[str, str], str | None]:
    config = getattr(resolved_config, "config", None)
    if config is None:
        return None, None, {}, None
    provider = _resolve_role_value(config=config, role=role, attr_name="provider")
    section_name = "openai_compatible" if provider == "openai_compatible" else "gemini"
    section = _resolve_role_value(config=config, role=role, attr_name=section_name)
    model = getattr(section, "model", None) if section is not None else None
    role_models = {role: model} if model else {}
    return provider, model, role_models, _fingerprint_config(config)


def _build_artifact_refs(*, artifacts: dict[str, str], scope: str) -> dict[str, dict[str, Any]]:
    refs: dict[str, dict[str, Any]] = {}
    for artifact_id, raw_path in artifacts.items():
        path = Path(raw_path)
        refs[artifact_id] = {
            "artifact_id": artifact_id,
            "role": artifact_id,
            "kind": _infer_kind(path),
            "scope": scope,
            "path": str(path),
            "media_type": _infer_media_type(path),
            "exists": path.exists(),
            "metadata": {},
        }
    return refs


def _infer_kind(path: Path) -> str:
    if path.is_dir():
        if path.name in {"raw", "annotated"}:
            return "image_directory"
        return "directory"
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "json_file"
    if suffix == ".jsonl":
        return "jsonl_file"
    if suffix == ".log":
        return "log_file"
    if suffix in {".txt", ".md", ".xml", ".yaml", ".yml"}:
        return "text_file"
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return "binary_file"
    return "other_file"


def _infer_media_type(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "application/json"
    if suffix == ".jsonl":
        return "application/x-ndjson"
    if suffix == ".log":
        return "text/plain"
    if suffix in {".txt", ".md"}:
        return "text/plain"
    if suffix == ".xml":
        return "application/xml"
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return None


def _resolve_role_value(*, config: Any, role: str, attr_name: str) -> Any:
    agents = getattr(config, "agents", None)
    role_config = getattr(agents, role, None) if agents is not None else None
    value = getattr(role_config, attr_name, None) if role_config is not None else None
    if value is not None:
        return value
    return getattr(config, attr_name, None)


def _fingerprint_config(config: Any) -> str | None:
    if not hasattr(config, "model_dump"):
        return None
    payload = config.model_dump(mode="json", exclude_none=True)
    _mask_provider_secret(payload.get("openai_compatible"))
    _mask_provider_secret(payload.get("gemini"))
    agents = payload.get("agents")
    if isinstance(agents, dict):
        for role_payload in cast(dict[str, Any], agents).values():
            if not isinstance(role_payload, dict):
                continue
            _mask_provider_secret(role_payload.get("openai_compatible"))
            _mask_provider_secret(role_payload.get("gemini"))
    canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _mask_provider_secret(section: Any) -> None:
    if isinstance(section, dict):
        section["api_key"] = None

def _discover_manifest_from_executable() -> Path | None:
    executable = Path(sys.executable).resolve()
    search_roots = [executable.parent, executable.parent.parent, executable.parent.parent.parent]
    for root in search_roots:
        candidate = root / _MANIFEST_NAME
        if candidate.exists():
            return candidate
    return None
