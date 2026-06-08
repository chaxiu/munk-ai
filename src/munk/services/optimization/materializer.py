from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from munk.optimizing import OptimizeRequest, OptimizeResult


class OptimizeFieldDiffItem(BaseModel):
    field_name: str
    reason: str | None = None
    before: list[str] = Field(default_factory=list)
    after: list[str] = Field(default_factory=list)
    changed: bool = False


class OptimizeFieldDiffBundle(BaseModel):
    operation_id: str
    case_id: str
    summary: str
    items: list[OptimizeFieldDiffItem] = Field(default_factory=list)


class OptimizeArtifactMaterializer:
    def paths(self, *, run_dir: Path) -> dict[str, Path]:
        root = run_dir / "optimize"
        root.mkdir(parents=True, exist_ok=True)
        return {
            "root": root,
            "request": root / "optimization_request.json",
            "result": root / "optimization_result.json",
            "diagnostics": root / "diagnostics.json",
            "field_diffs": root / "field_diffs.json",
        }

    @staticmethod
    def write_request(path: Path, request: OptimizeRequest) -> None:
        path.write_text(request.model_dump_json(indent=2), encoding="utf-8")

    @staticmethod
    def write_result(path: Path, result: OptimizeResult) -> None:
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    @staticmethod
    def write_field_diffs(path: Path, bundle: OptimizeFieldDiffBundle) -> None:
        path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")

    @staticmethod
    def write_diagnostics(
        path: Path,
        *,
        patched_fields: list[str],
        status: str,
        summary: str,
        applied: bool,
        skip_reason: str | None,
        confidence: float | None,
        field_diff_count: int,
    ) -> None:
        payload = {
            "status": status,
            "patched_fields": patched_fields,
            "summary": summary,
            "applied": applied,
            "skip_reason": skip_reason,
            "confidence": confidence,
            "field_diff_count": field_diff_count,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
