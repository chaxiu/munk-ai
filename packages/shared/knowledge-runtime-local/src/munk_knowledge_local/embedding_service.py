from __future__ import annotations

from pathlib import Path

import numpy as np

from .errors import KnowledgeEmbeddingError
from .onnx_embedding_loader import OnnxEmbeddingModel


class OnnxEmbeddingService:
    def __init__(
        self,
        *,
        model_dir: Path,
        model_id: str,
        onnx_file: str,
        embedding_dim: int,
    ) -> None:
        self._model_dir = model_dir
        self._model_id = model_id
        self._onnx_file = onnx_file
        self._embedding_dim = embedding_dim
        self._model: OnnxEmbeddingModel | None = None

    @property
    def model_dir(self) -> Path:
        return self._model_dir

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def embedding_dim(self) -> int:
        return self._embedding_dim

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        prepared = [self._with_prefix("search_document", text) for text in texts]
        return self._encode(prepared)

    def encode_query(self, text: str) -> np.ndarray:
        prepared = [self._with_prefix("search_query", text)]
        return self._encode(prepared)[0]

    def _encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        model = self._get_model()
        try:
            embeddings = model.encode(texts)
        except Exception as exc:  # pragma: no cover - depends on local model/runtime
            raise KnowledgeEmbeddingError(f"failed to encode knowledge texts with {self._model_id}: {exc}") from exc
        array = np.asarray(embeddings, dtype=np.float32)
        if array.ndim == 1:
            array = np.expand_dims(array, axis=0)
        return array

    def _get_model(self) -> OnnxEmbeddingModel:
        if self._model is not None:
            return self._model
        onnx_path = self._model_dir / self._onnx_file
        if not onnx_path.exists():
            raise KnowledgeEmbeddingError(f"knowledge embedding model not found: expected {onnx_path}")
        try:
            self._model = OnnxEmbeddingModel(
                model_dir=self._model_dir,
                onnx_file=self._onnx_file,
                embedding_dim=self._embedding_dim,
            )
        except Exception as exc:  # pragma: no cover - depends on local model/runtime
            raise KnowledgeEmbeddingError(
                f"failed to load knowledge embedding model from {self._model_dir}: {exc}"
            ) from exc
        return self._model

    @staticmethod
    def _with_prefix(prefix: str, text: str) -> str:
        normalized = text.strip()
        return f"{prefix}: {normalized}" if normalized else f"{prefix}:"
