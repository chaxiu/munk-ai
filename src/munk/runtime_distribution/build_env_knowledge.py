from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from munk.runtime_distribution.build_env_downloads import download_with_proxy_support, load_json_with_detected_proxy

KNOWLEDGE_EMBED_MODEL_CONFIG_KEY = "knowledge_embed_model"
KNOWLEDGE_EMBED_MODEL_MARKER_FILE = ".munk-knowledge-embed-model.json"
KNOWLEDGE_EMBED_MODEL_ONNX_RELPATH = Path("onnx") / "model_int8.onnx"
KNOWLEDGE_EMBED_MODEL_PROJECT_RELPATH = (
    Path("packages") / "shared" / "knowledge-runtime-local" / "src" / "munk_knowledge_local" / "resources" / "models"
)
SHA256_HEX_LENGTH = 64


@dataclass(frozen=True)
class KnowledgeEmbedModelRelease:
    name: str
    version: str
    url: str
    sha256: str
    manifest_url: str | None = None


def load_knowledge_embed_model_release(*, config_path: Path) -> KnowledgeEmbedModelRelease:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid runtime version config: expected object in {config_path}")
    payload_dict = cast(dict[str, Any], payload)
    model_config = payload_dict.get(KNOWLEDGE_EMBED_MODEL_CONFIG_KEY)
    if not isinstance(model_config, dict):
        raise RuntimeError(f"invalid runtime version config: missing '{KNOWLEDGE_EMBED_MODEL_CONFIG_KEY}' in {config_path}")
    pinned = knowledge_embed_model_release_from_payload(model_config)
    if pinned.manifest_url is None:
        return pinned
    remote = knowledge_embed_model_release_from_payload(
        load_json_with_detected_proxy(pinned.manifest_url),
        manifest_url=pinned.manifest_url,
    )
    if remote != pinned:
        raise RuntimeError(
            "remote knowledge embed model manifest does not match pinned runtime version config: "
            f"pinned={pinned} remote={remote}"
        )
    return pinned


def resolve_knowledge_embed_model_dir(*, project_root: Path, release: KnowledgeEmbedModelRelease) -> Path:
    return project_root / KNOWLEDGE_EMBED_MODEL_PROJECT_RELPATH / Path(release.name).stem


def prepare_knowledge_embed_model(
    *,
    project_root: Path,
    download_dir: Path,
    version_config_path: Path,
    force: bool = False,
) -> Path:
    release = load_knowledge_embed_model_release(config_path=version_config_path)
    model_dir = resolve_knowledge_embed_model_dir(project_root=project_root, release=release)
    if not force and knowledge_embed_model_installation_matches(model_dir=model_dir, release=release):
        return model_dir
    download_dir.mkdir(parents=True, exist_ok=True)
    archive_path = download_dir / Path(release.url).name
    if force and archive_path.exists() and knowledge_embed_model_archive_matches(archive_path=archive_path, release=release):
        print(f"reusing knowledge embed model archive: {archive_path}")
    elif force or not archive_path.exists():
        print(f"downloading knowledge embed model: {release.url}")
        download_with_proxy_support(url=release.url, destination=archive_path)
    verify_knowledge_embed_model_archive(archive_path=archive_path, expected_sha256=release.sha256)
    extract_knowledge_embed_model_archive(archive_path=archive_path, destination_dir=model_dir)
    write_knowledge_embed_model_marker(model_dir=model_dir, release=release)
    return model_dir


def verify_knowledge_embed_model_archive(*, archive_path: Path, expected_sha256: str) -> None:
    actual_sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    if actual_sha256 != expected_sha256:
        raise RuntimeError(
            "knowledge embed model archive sha256 mismatch: "
            f"expected={expected_sha256} actual={actual_sha256} path={archive_path}"
        )


def knowledge_embed_model_archive_matches(*, archive_path: Path, release: KnowledgeEmbedModelRelease) -> bool:
    try:
        verify_knowledge_embed_model_archive(archive_path=archive_path, expected_sha256=release.sha256)
    except RuntimeError:
        return False
    return True


def extract_knowledge_embed_model_archive(*, archive_path: Path, destination_dir: Path) -> None:
    if destination_dir.exists():
        shutil.rmtree(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="munk-knowledge-embed-model-") as temp_dir:
        temp_root = Path(temp_dir)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(temp_root)
        extracted_children = [child for child in temp_root.iterdir() if child.name != "__MACOSX"]
        extracted_root = extracted_children[0] if len(extracted_children) == 1 and extracted_children[0].is_dir() else temp_root
        for child in extracted_root.iterdir():
            shutil.move(str(child), str(destination_dir / child.name))
    onnx_path = destination_dir / KNOWLEDGE_EMBED_MODEL_ONNX_RELPATH
    if not onnx_path.exists():
        raise RuntimeError(f"knowledge embed model archive did not contain ONNX file: {onnx_path}")


def knowledge_embed_model_release_from_payload(
    payload: object,
    *,
    manifest_url: str | None = None,
) -> KnowledgeEmbedModelRelease:
    if not isinstance(payload, dict):
        raise RuntimeError("invalid knowledge embed model release payload: expected object")
    payload_dict = cast(dict[str, Any], payload)
    name = payload_dict.get("name")
    version = payload_dict.get("version")
    url = payload_dict.get("url")
    sha256 = payload_dict.get("sha256")
    if not isinstance(name, str) or not name.strip():
        raise RuntimeError("invalid knowledge embed model release payload: bad name")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError("invalid knowledge embed model release payload: bad version")
    if not isinstance(url, str) or not url.strip():
        raise RuntimeError("invalid knowledge embed model release payload: bad url")
    if not isinstance(sha256, str) or len(sha256.strip()) != SHA256_HEX_LENGTH:
        raise RuntimeError("invalid knowledge embed model release payload: bad sha256")
    normalized_manifest_url = None
    manifest_url_value = payload_dict.get("manifest_url") if manifest_url is None else manifest_url
    if isinstance(manifest_url_value, str) and manifest_url_value.strip():
        normalized_manifest_url = manifest_url_value.strip()
    return KnowledgeEmbedModelRelease(
        name=name.strip(),
        version=version.strip(),
        url=url.strip(),
        sha256=sha256.strip().lower(),
        manifest_url=normalized_manifest_url,
    )


def knowledge_embed_model_installation_matches(*, model_dir: Path, release: KnowledgeEmbedModelRelease) -> bool:
    marker_path = model_dir / KNOWLEDGE_EMBED_MODEL_MARKER_FILE
    onnx_path = model_dir / KNOWLEDGE_EMBED_MODEL_ONNX_RELPATH
    if not marker_path.exists() or not onnx_path.exists():
        return False
    try:
        payload = json.loads(marker_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return payload == knowledge_embed_model_marker_payload(release=release)


def write_knowledge_embed_model_marker(*, model_dir: Path, release: KnowledgeEmbedModelRelease) -> None:
    marker_path = model_dir / KNOWLEDGE_EMBED_MODEL_MARKER_FILE
    marker_path.write_text(
        json.dumps(knowledge_embed_model_marker_payload(release=release), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def knowledge_embed_model_marker_payload(*, release: KnowledgeEmbedModelRelease) -> dict[str, str]:
    payload = {
        "name": release.name,
        "version": release.version,
        "url": release.url,
        "sha256": release.sha256,
    }
    if release.manifest_url is not None:
        payload["manifest_url"] = release.manifest_url
    return payload
