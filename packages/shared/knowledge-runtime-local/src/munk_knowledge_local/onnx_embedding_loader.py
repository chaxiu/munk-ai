from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

_MEAN_POOLING_KEY = "pooling_mode_mean_tokens"
_POOLING_CONFIG_RELATIVE_PATH = Path("1_Pooling") / "config.json"
_DEFAULT_MAX_LENGTH_LIMIT = 8192


class OnnxEmbeddingModel:
    """Minimal local ONNX embedding runner for knowledge retrieval."""

    def __init__(
        self,
        *,
        model_dir: Path,
        onnx_file: str,
        embedding_dim: int,
        provider: str = "CPUExecutionProvider",
    ) -> None:
        self._model_dir = model_dir
        self._embedding_dim = embedding_dim
        self._pooling_mode = self._load_pooling_mode(model_dir)
        self._tokenizer = AutoTokenizer.from_pretrained(
            str(model_dir),
            local_files_only=True,
            trust_remote_code=False,
            use_fast=True,
        )
        model_path = model_dir / onnx_file
        self._session = ort.InferenceSession(str(model_path), providers=[provider])
        self._input_names = {item.name for item in self._session.get_inputs()}
        outputs = self._session.get_outputs()
        if not outputs:
            raise ValueError(f"knowledge embedding ONNX model has no outputs: {model_path}")
        self._output_name = outputs[0].name
        self._max_length = self._resolve_max_length()

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self._embedding_dim), dtype=np.float32)
        encoded_inputs = self._tokenize(texts)
        session_inputs = {
            name: value
            for name, value in encoded_inputs.items()
            if name in self._input_names
        }
        model_outputs = self._session.run([self._output_name], session_inputs)
        if not model_outputs:
            raise ValueError("knowledge embedding ONNX session returned no outputs")
        last_hidden_state = np.asarray(model_outputs[0], dtype=np.float32)
        embeddings = self._pool(last_hidden_state, encoded_inputs["attention_mask"])
        if embeddings.shape[1] != self._embedding_dim:
            raise ValueError(
                f"knowledge embedding dimension mismatch: expected {self._embedding_dim}, got {embeddings.shape[1]}"
            )
        return self._normalize(embeddings)

    def _tokenize(self, texts: list[str]) -> dict[str, np.ndarray]:
        tokenizer_output: dict[str, Any] = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self._max_length,
            return_tensors="np",
        )
        input_ids = np.asarray(tokenizer_output["input_ids"], dtype=np.int64)
        attention_mask = np.asarray(tokenizer_output["attention_mask"], dtype=np.int64)
        token_type_ids = tokenizer_output.get("token_type_ids")
        if token_type_ids is None:
            token_type_ids = np.zeros_like(input_ids, dtype=np.int64)
        else:
            token_type_ids = np.asarray(token_type_ids, dtype=np.int64)
        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "token_type_ids": token_type_ids,
        }

    def _pool(self, last_hidden_state: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
        if self._pooling_mode != _MEAN_POOLING_KEY:
            raise ValueError(f"unsupported knowledge pooling mode: {self._pooling_mode}")
        mask = np.asarray(attention_mask, dtype=np.float32)[..., None]
        mask_sum = np.clip(mask.sum(axis=1), a_min=1e-12, a_max=None)
        return np.asarray((last_hidden_state * mask).sum(axis=1) / mask_sum, dtype=np.float32)

    def _resolve_max_length(self) -> int | None:
        model_max_length = getattr(self._tokenizer, "model_max_length", None)
        if isinstance(model_max_length, int) and 0 < model_max_length <= _DEFAULT_MAX_LENGTH_LIMIT:
            return model_max_length
        return None

    @staticmethod
    def _normalize(embeddings: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / np.clip(norms, a_min=1e-12, a_max=None)
        return np.asarray(normalized, dtype=np.float32)

    @staticmethod
    def _load_pooling_mode(model_dir: Path) -> str:
        config_path = model_dir / _POOLING_CONFIG_RELATIVE_PATH
        if not config_path.exists():
            raise ValueError(f"knowledge embedding pooling config is missing: {config_path}")
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        truthy_keys = [
            key
            for key, value in payload.items()
            if key.startswith("pooling_mode_") and bool(value)
        ]
        if truthy_keys != [_MEAN_POOLING_KEY]:
            raise ValueError(
                f"knowledge embedding pooling config must enable only {_MEAN_POOLING_KEY}: {config_path}"
            )
        return truthy_keys[0]
