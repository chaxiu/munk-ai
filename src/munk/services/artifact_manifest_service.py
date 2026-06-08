from __future__ import annotations

import json
from pathlib import Path

from munk.execution.models import CaseExecutionResult, JudgeVerdict
from munk.services.artifact_manifest_models import (
    ArtifactKind,
    ArtifactManifest,
    ArtifactRef,
    ArtifactScope,
    CaseArtifactEntry,
    ReproductionEntry,
    ReproductionTargetKind,
)


class ArtifactManifestService:
    def build_operation_manifest(
        self,
        *,
        root_dir: Path,
        artifacts: dict[str, str],
        operation_id: str | None = None,
        operation_kind: ReproductionTargetKind | None = None,
        verification_verdict: JudgeVerdict | None = None,
        reproduction: list[ReproductionEntry] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ArtifactManifest:
        return ArtifactManifest(
            operation_id=operation_id,
            operation_kind=operation_kind,
            verification_verdict=verification_verdict,
            root_dir=root_dir,
            primary_artifacts=self.build_artifact_refs(
                artifacts=artifacts,
                scope="operation",
            ),
            case_runs=[],
            reproduction=list(reproduction or []),
            metadata=dict(metadata or {}),
        )

    def build_case_manifest(
        self,
        *,
        run_dir: Path,
        artifacts: dict[str, str],
        case_id: str,
        title: str,
        verdict: JudgeVerdict,
        execution_status: str,
        operation_id: str | None = None,
        operation_kind: ReproductionTargetKind | None = None,
        verification_verdict: JudgeVerdict | None = None,
        reproduction: list[ReproductionEntry] | None = None,
    ) -> ArtifactManifest:
        return ArtifactManifest(
            operation_id=operation_id,
            operation_kind=operation_kind,
            verification_verdict=verification_verdict,
            root_dir=run_dir,
            primary_artifacts=self.build_artifact_refs(
                artifacts=artifacts,
                scope="case_run",
            ),
            case_runs=[
                CaseArtifactEntry(
                    case_id=case_id,
                    title=title,
                    operation_id=operation_id,
                    verdict=verdict,
                    execution_status=execution_status,
                    run_dir=run_dir,
                    artifacts=self.build_artifact_refs(
                        artifacts=artifacts,
                        scope="case_run",
                    ),
                )
            ],
            reproduction=list(reproduction or []),
            metadata={"case_count": 1},
        )

    def build_plan_manifest(
        self,
        *,
        root_dir: Path,
        artifacts: dict[str, str],
        case_results: list[CaseExecutionResult],
        case_operation_ids: dict[str, str | None] | None = None,
        case_titles: dict[str, str] | None = None,
        operation_id: str | None = None,
        operation_kind: ReproductionTargetKind | None = None,
        verification_verdict: JudgeVerdict | None = None,
        reproduction: list[ReproductionEntry] | None = None,
    ) -> ArtifactManifest:
        return ArtifactManifest(
            operation_id=operation_id,
            operation_kind=operation_kind,
            verification_verdict=verification_verdict,
            root_dir=root_dir,
            primary_artifacts=self.build_artifact_refs(
                artifacts=artifacts,
                scope="plan_run",
            ),
            case_runs=[
                self._case_entry_from_result(
                    item,
                    operation_id=(case_operation_ids or {}).get(item.case_id),
                    title=(case_titles or {}).get(item.case_id),
                )
                for item in case_results
            ],
            reproduction=list(reproduction or []),
            metadata={"case_count": len(case_results)},
        )

    def build_artifact_refs(
        self,
        *,
        artifacts: dict[str, str],
        scope: ArtifactScope,
    ) -> dict[str, ArtifactRef]:
        refs: dict[str, ArtifactRef] = {}
        for artifact_id, raw_path in artifacts.items():
            path = Path(raw_path)
            refs[artifact_id] = ArtifactRef(
                artifact_id=artifact_id,
                role=artifact_id,
                kind=self._infer_kind(path),
                scope=scope,
                path=path,
                media_type=self._infer_media_type(path),
                exists=path.exists(),
                metadata={},
            )
        return refs

    def write_manifest(self, path: Path, manifest: ArtifactManifest) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = manifest.model_dump(mode="json")
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        refreshed_manifest = self._refresh_manifest_exists(manifest)
        refreshed_payload = refreshed_manifest.model_dump(mode="json")
        if refreshed_payload != payload:
            path.write_text(
                json.dumps(refreshed_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def load_manifest(self, path: Path) -> ArtifactManifest:
        return ArtifactManifest.model_validate_json(path.read_text(encoding="utf-8"))

    def with_reproduction(
        self,
        manifest: ArtifactManifest,
        *,
        reproduction: list[ReproductionEntry],
    ) -> ArtifactManifest:
        return manifest.model_copy(update={"reproduction": list(reproduction)})

    def _case_entry_from_result(
        self,
        result: CaseExecutionResult,
        *,
        operation_id: str | None = None,
        title: str | None = None,
    ) -> CaseArtifactEntry:
        return CaseArtifactEntry(
            case_id=result.case_id,
            title=title or result.summary or result.case_id,
            operation_id=operation_id,
            verdict=result.verdict,
            execution_status=result.execution.status,
            run_dir=result.run_dir,
            artifacts=self.build_artifact_refs(
                artifacts=result.artifacts,
                scope="case_run",
            ),
        )

    @staticmethod
    def _infer_kind(path: Path) -> ArtifactKind:
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

    @staticmethod
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

    @staticmethod
    def _refresh_manifest_exists(manifest: ArtifactManifest) -> ArtifactManifest:
        def refresh_refs(refs: dict[str, ArtifactRef]) -> dict[str, ArtifactRef]:
            return {
                artifact_id: ref.model_copy(update={"exists": ref.path.exists()})
                for artifact_id, ref in refs.items()
            }

        return manifest.model_copy(
            update={
                "primary_artifacts": refresh_refs(manifest.primary_artifacts),
                "case_runs": [
                    case_run.model_copy(update={"artifacts": refresh_refs(case_run.artifacts)})
                    for case_run in manifest.case_runs
                ],
            }
        )
