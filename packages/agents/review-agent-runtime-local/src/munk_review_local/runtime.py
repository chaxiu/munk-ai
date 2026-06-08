from __future__ import annotations

from typing import Any

from munk.reviewing.health import ReviewRuntimeHealth

from .constants import (
    DEFAULT_REVIEW_BUILD_MANIFEST_NAME,
    DEFAULT_REVIEW_MODEL_DIR,
    resolve_runtime_review_build_root,
)
from .knowledge_db import resolve_runtime_review_db_path
from .knowledge_source import review_knowledge_root
from .service import ReviewService


class LocalReviewRuntime:
    def __init__(self, *, resolved_config: Any) -> None:
        self._service = ReviewService(resolved_config=resolved_config)

    def review(self, request, *, context, cancel_controller=None):  # noqa: ANN001
        return self._service.review(
            request,
            context=context,
            cancel_controller=cancel_controller,
        )


class LocalReviewRuntimeFactory:
    runtime_id = "local"

    def create_runtime(self, *, resolved_config: Any) -> LocalReviewRuntime:
        return LocalReviewRuntime(resolved_config=resolved_config)

    def diagnose(self) -> ReviewRuntimeHealth:
        knowledge_root = review_knowledge_root()
        build_root = resolve_runtime_review_build_root()
        db_path = resolve_runtime_review_db_path()
        build_manifest_path = build_root / DEFAULT_REVIEW_BUILD_MANIFEST_NAME
        details = {
            "knowledge_root": str(knowledge_root),
            "build_root": str(build_root),
            "db_path": str(db_path),
            "build_manifest_path": str(build_manifest_path),
            "model_dir": str(DEFAULT_REVIEW_MODEL_DIR),
        }
        if not knowledge_root.exists():
            return ReviewRuntimeHealth(
                runtime_id=self.runtime_id,
                status="error",
                message="review knowledge root is missing",
                details=details,
            )
        if not DEFAULT_REVIEW_MODEL_DIR.exists():
            return ReviewRuntimeHealth(
                runtime_id=self.runtime_id,
                status="error",
                message="review embedding model directory is missing",
                details=details,
            )
        if not db_path.exists():
            return ReviewRuntimeHealth(
                runtime_id=self.runtime_id,
                status="error",
                message="review knowledge database is missing",
                details=details,
            )
        if not build_manifest_path.exists():
            return ReviewRuntimeHealth(
                runtime_id=self.runtime_id,
                status="error",
                message="review knowledge build manifest is missing",
                details=details,
            )
        return ReviewRuntimeHealth(
            runtime_id=self.runtime_id,
            status="ok",
            message="review local runtime is available",
            details=details,
        )


def build_review_runtime_factory() -> LocalReviewRuntimeFactory:
    return LocalReviewRuntimeFactory()
