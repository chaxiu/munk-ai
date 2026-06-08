from __future__ import annotations

from pathlib import Path
from typing import Any

from munk.execution.models import ExecutedPlanResult, PhasedOperationResult
from munk.services.artifact_manifest_service import ArtifactManifestService
from munk.services.operations.models import VerificationVerdict
from munk.services.operations.service import OperationTracker
from munk.token_usage import TokenUsage, merge_token_usages


def build_executed_plan_result(result) -> ExecutedPlanResult:  # noqa: ANN001
    return ExecutedPlanResult(
        verification_status=result.status,
        total_cases=result.total_cases,
        passed_cases=result.passed_cases,
        failed_cases=result.failed_cases,
        inconclusive_cases=result.inconclusive_cases,
        stopped_early=result.stopped_early,
        items=list(result.items),
        summary_path=result.summary_path,
        report_path=result.report_path,
        diagnostics_path=result.diagnostics_path,
        token_usage=result.token_usage,
    )


def build_phased_operation_data(result: PhasedOperationResult) -> dict[str, Any]:
    return dict(result.model_dump(mode="json"))


def build_execution_artifacts(execution_result: ExecutedPlanResult) -> dict[str, str]:
    artifacts = {
        "summary": str(execution_result.summary_path),
        "report": str(execution_result.report_path),
        "execution_plan": str(execution_result.summary_path.parent / "plan.json"),
    }
    if execution_result.diagnostics_path is not None:
        artifacts["diagnostics"] = str(execution_result.diagnostics_path)
    if execution_result.upstream_review_result_path is not None:
        artifacts["upstream_review_result"] = str(execution_result.upstream_review_result_path)
    if execution_result.upstream_review_orchestration_path is not None:
        artifacts["review_orchestration"] = str(execution_result.upstream_review_orchestration_path)
    return artifacts


def load_contract_versions(
    *,
    manifest_path: Path,
    fallback: dict[str, str | None],
) -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    if manifest_path.exists():
        try:
            manifest = ArtifactManifestService().load_manifest(manifest_path)
        except Exception:
            pass
        else:
            versions.update(manifest.schema_versions)
    for key, value in fallback.items():
        if value is not None and key not in versions:
            versions[key] = value
    return versions


def artifact_manifest_version(manifest_path: Path) -> int | None:
    if not manifest_path.exists():
        return None
    try:
        manifest = ArtifactManifestService().load_manifest(manifest_path)
    except Exception:
        return None
    return manifest.manifest_version


def merged_tracker_artifacts(
    tracker: OperationTracker,
    result_artifacts: dict[str, Any],
) -> dict[str, str]:
    current = dict(tracker.get_record().artifacts_json)
    current.update(stringify_artifacts(result_artifacts))
    return current


def verdict_from_execution_status(status: str) -> VerificationVerdict:
    if status == "failed":
        return "failed"
    if status in {"inconclusive", "stopped"}:
        return "inconclusive"
    return "passed"


def result_is_cancelled(exc: Exception) -> bool:
    return exc.__class__.__name__ == "OperationCancelledError"


def stringify_artifacts(artifacts: dict[str, Any]) -> dict[str, str]:
    return {key: str(value) for key, value in artifacts.items()}


def merge_scene_usages(*usages: TokenUsage | None) -> TokenUsage | None:
    return merge_token_usages(usages)
