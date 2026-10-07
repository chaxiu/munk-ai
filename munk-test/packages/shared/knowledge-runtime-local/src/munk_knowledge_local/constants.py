from __future__ import annotations

from pathlib import Path

DEFAULT_APP_KNOWLEDGE_DB_NAME = "app_knowledge.sqlite"
DEFAULT_APP_KNOWLEDGE_BUILD_MANIFEST_NAME = "build_manifest.json"
DEFAULT_APP_KNOWLEDGE_MODEL_DIRNAME = "nomic-embed-text-v1.5"
DEFAULT_APP_KNOWLEDGE_MODEL_ID = "nomic-embed-text-v1.5-onnxrt-v1"
DEFAULT_APP_KNOWLEDGE_EMBEDDING_DIM = 768
DEFAULT_APP_KNOWLEDGE_ONNX_FILE = "onnx/model_int8.onnx"


def package_root() -> Path:
    return Path(__file__).resolve().parent


def knowledge_resource_root() -> Path:
    return package_root() / "resources"


def default_app_knowledge_model_dir() -> Path:
    return knowledge_resource_root() / "models" / DEFAULT_APP_KNOWLEDGE_MODEL_DIRNAME
