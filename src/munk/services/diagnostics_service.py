from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, Any, cast

from munk.config import ResolvedConfig, resolve_role_model_config
from munk.running import RunnerProtocolError
from munk.services.diagnostics_models import ArtifactCheck, DiagnosticsFailureCategory, OperationDiagnostics

if TYPE_CHECKING:
    from munk.config.schema import AgentRole


class OperationDiagnosticsService:
    def write(self, path: Path, diagnostics: OperationDiagnostics) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(diagnostics.model_dump_json(indent=2), encoding="utf-8")

    def load(self, path: Path) -> OperationDiagnostics:
        return OperationDiagnostics.model_validate_json(path.read_text(encoding="utf-8"))

    @staticmethod
    def build_json_artifact_check(
        *,
        artifact_id: str,
        path: Path,
        required_fields: tuple[str, ...] = (),
        expected_schema_version: str | None = None,
        required: bool = True,
    ) -> ArtifactCheck:
        exists = path.exists()
        if not exists:
            return ArtifactCheck(
                artifact_id=artifact_id,
                path=path,
                required=required,
                exists=False,
                valid=False,
                summary="artifact not found",
            )

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            return ArtifactCheck(
                artifact_id=artifact_id,
                path=path,
                required=required,
                exists=True,
                valid=False,
                summary=f"invalid json: {exc}",
            )

        missing_fields = [field for field in required_fields if field not in payload]
        if missing_fields:
            return ArtifactCheck(
                artifact_id=artifact_id,
                path=path,
                required=required,
                exists=True,
                valid=False,
                summary=f"missing fields: {', '.join(missing_fields)}",
            )

        if expected_schema_version is not None and payload.get("schema_version") != expected_schema_version:
            return ArtifactCheck(
                artifact_id=artifact_id,
                path=path,
                required=required,
                exists=True,
                valid=False,
                summary=(
                    "unexpected schema_version: "
                    f"{payload.get('schema_version')!r} != {expected_schema_version!r}"
                ),
            )

        return ArtifactCheck(
            artifact_id=artifact_id,
            path=path,
            required=required,
            exists=True,
            valid=True,
            summary="ok",
        )

    @staticmethod
    def build_path_artifact_check(
        *,
        artifact_id: str,
        path: Path,
        required: bool = True,
    ) -> ArtifactCheck:
        exists = path.exists()
        return ArtifactCheck(
            artifact_id=artifact_id,
            path=path,
            required=required,
            exists=exists,
            valid=exists,
            summary="ok" if exists else "artifact not found",
        )

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def timer() -> float:
        return perf_counter()

    @staticmethod
    def elapsed_ms(start_time: float) -> int:
        return max(0, int((perf_counter() - start_time) * 1000))

    @staticmethod
    def resolve_provider_model(
        *,
        resolved_config: ResolvedConfig | None,
        roles: tuple[AgentRole, ...],
    ) -> tuple[str | None, str | None, dict[str, str], str | None]:
        if resolved_config is None:
            return None, None, {}, None

        role_models: dict[str, str] = {}
        provider = None
        default_model = None
        for role in roles:
            resolved = resolve_role_model_config(resolved_config.config, role=role)
            if resolved is None:
                continue
            role_models[role] = resolved.model
            if provider is None:
                provider = resolved.provider
            if default_model is None:
                default_model = resolved.model
        provider = provider or resolved_config.config.provider
        fingerprint = OperationDiagnosticsService._fingerprint_config(resolved_config.config)
        return provider, default_model, role_models, fingerprint

    @staticmethod
    def classify_exception(exc: Exception) -> DiagnosticsFailureCategory:
        name = exc.__class__.__name__.lower()
        message = str(exc).lower()
        text = f"{name} {message}"
        if (
            isinstance(exc, RunnerProtocolError)
            or "terminal tool contract" in text
            or "without terminal action" in text
            or "without valid structured action" in text
            or "structured action output" in text
        ):
            return "protocol_error"
        if isinstance(exc, json.JSONDecodeError):
            return "contract_error"
        if "artifact" in text or "manifest" in text:
            return "artifact_error"
        if "retrieval" in text or "embedding" in text or "sqlite-vec" in text:
            return "retrieval_error"
        if "plan" in text or "planner" in text:
            return "planning_error"
        if "execute" in text or "runtime override" in text or "run failed" in text:
            return "execution_error"
        if "model" in text or "openai" in text or "gemini" in text or "config" in text:
            return "model_error"
        if isinstance(exc, ValueError):
            return "contract_error"
        if isinstance(exc, FileNotFoundError):
            return "artifact_error"
        return "unknown_error"

    @staticmethod
    def failed_artifact_count(checks: list[ArtifactCheck]) -> int:
        return sum(1 for check in checks if check.required and (not check.exists or not check.valid))

    @staticmethod
    def _fingerprint_config(config) -> str:  # noqa: ANN001
        payload = cast(dict[str, Any], config.model_dump(mode="json", exclude_none=True))
        _mask_provider_secret(payload.get("openai_compatible"))
        _mask_provider_secret(payload.get("gemini"))
        agents = payload.get("agents")
        if isinstance(agents, dict):
            for role_payload in agents.values():
                if not isinstance(role_payload, dict):
                    continue
                _mask_provider_secret(role_payload.get("openai_compatible"))
                _mask_provider_secret(role_payload.get("gemini"))
        canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _mask_provider_secret(section) -> None:  # noqa: ANN001
    if isinstance(section, dict):
        section["api_key"] = None
