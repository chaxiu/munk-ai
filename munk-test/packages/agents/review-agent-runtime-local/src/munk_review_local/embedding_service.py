from __future__ import annotations

from pathlib import Path

from munk_knowledge_local.embedding_service import OnnxEmbeddingService

from .constants import (
    DEFAULT_REVIEW_EMBEDDING_DIM,
    DEFAULT_REVIEW_MODEL_DIR,
    DEFAULT_REVIEW_MODEL_ID,
    DEFAULT_REVIEW_ONNX_FILE,
)


class ReviewEmbeddingError(RuntimeError):
    """Raised when the local review embedding model cannot be loaded or used."""


class ReviewEmbeddingService(OnnxEmbeddingService):
    def __init__(
        self,
        *,
        model_dir: Path | None = None,
        model_id: str = DEFAULT_REVIEW_MODEL_ID,
        onnx_file: str = DEFAULT_REVIEW_ONNX_FILE,
    ) -> None:
        super().__init__(
            model_dir=model_dir or DEFAULT_REVIEW_MODEL_DIR,
            model_id=model_id,
            onnx_file=onnx_file,
            embedding_dim=DEFAULT_REVIEW_EMBEDDING_DIM,
        )
