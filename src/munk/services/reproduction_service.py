from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from munk.execution.models import CaseExecutionRequest
from munk.services.artifact_manifest_models import ReproductionEntry, ReproductionTargetKind
from munk.services.artifact_manifest_service import ArtifactManifestService
from munk.services.operations.models import OperationRecord
from munk.services.operations.paths import operation_dir


@dataclass(frozen=True)
class ReproductionResult:
    repro_dir: Path
    entries: list[ReproductionEntry]


class ReproductionService:
    def __init__(self, manifest_service: ArtifactManifestService | None = None) -> None:
        self._manifest_service = manifest_service or ArtifactManifestService()

    def materialize(self, record: OperationRecord) -> ReproductionResult:
        repro_dir = self._resolve_repro_dir(record)
        repro_dir.mkdir(parents=True, exist_ok=True)
        entries = self._build_entries(record=record, repro_dir=repro_dir)
        return ReproductionResult(repro_dir=repro_dir, entries=entries)

    def _build_entries(self, *, record: OperationRecord, repro_dir: Path) -> list[ReproductionEntry]:
        entries = [self._write_original_request(record=record, repro_dir=repro_dir)]
        if record.kind in {"run_plan", "verify_change"}:
            entries.extend(self._write_failed_case_requests(record=record, repro_dir=repro_dir))
        return entries

    def _write_original_request(self, *, record: OperationRecord, repro_dir: Path) -> ReproductionEntry:
        request_path = repro_dir / "original-request.json"
        request_path.write_text(
            json.dumps(record.request_json, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return ReproductionEntry(
            target_kind=self._reproduction_target_kind(record.kind),
            source_operation_id=record.operation_id,
            command=self._command_for_kind(record.kind, request_path),
            request_file=request_path,
            reason="replay original machine request",
        )

    def _write_failed_case_requests(
        self,
        *,
        record: OperationRecord,
        repro_dir: Path,
    ) -> list[ReproductionEntry]:
        manifest_path = self._manifest_path(record)
        if manifest_path is None or not manifest_path.exists():
            return []
        manifest = self._manifest_service.load_manifest(manifest_path)
        entries: list[ReproductionEntry] = []
        for case_run in manifest.case_runs:
            if case_run.verdict not in {"failed", "inconclusive"}:
                continue
            case_request_path = self._case_request_path(case_run.artifacts)
            if case_request_path is None or not case_request_path.exists():
                continue
            case_request = CaseExecutionRequest.model_validate_json(
                case_request_path.read_text(encoding="utf-8")
            )
            request_payload = {
                "app_id": case_request.app_id,
                "plan_id": case_request.plan_id,
                "case_id": case_request.case.case_id,
                "app_target": case_request.app_target.model_dump(mode="json"),
                "device_ref": case_request.device_ref,
                "artifact_path": str(case_request.artifact_path) if case_request.artifact_path else None,
                "runtime_overrides": dict(case_request.runtime_overrides),
            }
            request_file = repro_dir / f"run-case-{case_request.case.case_id}.json"
            request_file.write_text(
                json.dumps(request_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            entries.append(
                ReproductionEntry(
                    target_kind="run_case",
                    source_operation_id=record.operation_id,
                    command=self._command_for_kind("run_case", request_file),
                    request_file=request_file,
                    case_id=case_request.case.case_id,
                    reason=f"reproduce {case_run.verdict} case from {record.kind}",
                )
            )
        return entries

    @staticmethod
    def _case_request_path(artifacts: dict[str, Any]) -> Path | None:
        case_ref = artifacts.get("case")
        if case_ref is None:
            return None
        raw_path = getattr(case_ref, "path", None)
        if raw_path is None:
            return None
        return Path(raw_path)

    @staticmethod
    def _command_for_kind(kind: str, request_file: Path) -> str:
        if kind == "plan":
            return f"munk plan --request-file {request_file} --json"
        if kind == "run_case":
            return f"munk run case --request-file {request_file} --json"
        if kind == "run_plan":
            return f"munk run plan --request-file {request_file} --json"
        if kind == "run_plans":
            return f"munk run plans --request-file {request_file} --json"
        if kind == "verify_change":
            return f"munk verify change --request-file {request_file} --json"
        if kind == "review":
            return f"munk review --request-file {request_file} --json"
        raise ValueError(f"unsupported reproduction kind: {kind}")

    @staticmethod
    def _reproduction_target_kind(kind: str) -> ReproductionTargetKind:
        if kind in {"plan", "run_case", "run_plan", "run_plans", "verify_change", "review"}:
            return cast(ReproductionTargetKind, kind)
        raise ValueError(f"unsupported reproduction target kind: {kind}")

    def _resolve_repro_dir(self, record: OperationRecord) -> Path:
        root_dir = self._root_dir(record)
        return root_dir / "repro"

    def _root_dir(self, record: OperationRecord) -> Path:
        artifacts = record.artifacts_json
        for key in ("plan_run_dir", "run_dir"):
            raw_path = artifacts.get(key)
            if raw_path:
                return Path(raw_path)
        manifest_path = self._manifest_path(record)
        if manifest_path is not None:
            return manifest_path.parent
        return operation_dir(record.operation_id)

    def _manifest_path(self, record: OperationRecord) -> Path | None:
        raw_path = record.artifacts_json.get("artifact_manifest")
        if raw_path:
            return Path(raw_path)
        return None
