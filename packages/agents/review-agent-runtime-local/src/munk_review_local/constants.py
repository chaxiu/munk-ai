from __future__ import annotations

import os
from pathlib import Path

from munk_knowledge_local import (
    DEFAULT_APP_KNOWLEDGE_EMBEDDING_DIM,
    DEFAULT_APP_KNOWLEDGE_MODEL_DIRNAME,
    DEFAULT_APP_KNOWLEDGE_MODEL_ID,
    DEFAULT_APP_KNOWLEDGE_ONNX_FILE,
    default_app_knowledge_model_dir,
)

from .runtime_support import default_runtime_root

DEFAULT_REVIEW_KNOWLEDGE_DIRNAME = "review_knowledge"
DEFAULT_REVIEW_KNOWLEDGE_BUILD_DIRNAME = "build"
DEFAULT_REVIEW_DB_NAME = "review_knowledge.sqlite"
DEFAULT_REVIEW_BUILD_MANIFEST_NAME = "build_manifest.json"
DEFAULT_REVIEW_MODEL_DIRNAME = DEFAULT_APP_KNOWLEDGE_MODEL_DIRNAME
DEFAULT_REVIEW_MODEL_ID = DEFAULT_APP_KNOWLEDGE_MODEL_ID
DEFAULT_REVIEW_EMBEDDING_DIM = DEFAULT_APP_KNOWLEDGE_EMBEDDING_DIM
DEFAULT_REVIEW_ONNX_FILE = DEFAULT_APP_KNOWLEDGE_ONNX_FILE
_MUNK_HOME_ENV = "MUNK_HOME"
_RUNTIME_ROOT_ENV = "MUNK_RUNTIME_ROOT"
_REVIEW_RUNTIME_DATA_ROOT_ENV = "MUNK_REVIEW_RUNTIME_DATA_ROOT"


def package_root() -> Path:
    return Path(__file__).resolve().parent


def review_resource_root() -> Path:
    return package_root() / "resources"


def default_review_model_dir() -> Path:
    return default_app_knowledge_model_dir()


def default_review_source_root() -> Path:
    return review_resource_root() / DEFAULT_REVIEW_KNOWLEDGE_DIRNAME


def default_review_runtime_data_root() -> Path:
    configured = os.environ.get(_REVIEW_RUNTIME_DATA_ROOT_ENV)
    if configured:
        return Path(configured).expanduser()
    munk_home = os.environ.get(_MUNK_HOME_ENV)
    if munk_home:
        return Path(munk_home).expanduser() / "cache" / "review-runtime-local"
    runtime_root = os.environ.get(_RUNTIME_ROOT_ENV)
    if runtime_root:
        return Path(runtime_root).expanduser() / ".review-runtime-local"
    return default_runtime_root() / ".review-runtime-local"


def default_review_build_root(*, source_root: Path | None = None, build_root: Path | None = None) -> Path:
    if build_root is not None:
        return build_root
    if source_root is not None:
        return source_root / DEFAULT_REVIEW_KNOWLEDGE_BUILD_DIRNAME
    return default_review_source_root() / DEFAULT_REVIEW_KNOWLEDGE_BUILD_DIRNAME


def resolve_runtime_review_build_root() -> Path:
    return default_review_source_root() / DEFAULT_REVIEW_KNOWLEDGE_BUILD_DIRNAME


DEFAULT_REVIEW_MODEL_DIR = default_review_model_dir()
