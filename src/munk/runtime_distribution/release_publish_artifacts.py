from __future__ import annotations

import hashlib
import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .release_publish_models import (
    R2PublishConfig,
    ReleaseArtifactDescriptor,
    UploadObject,
    VERSION_MANIFEST_SCHEMA_VERSION,
)


def discover_release_artifacts(*, artifact_dir: Path, version: str) -> list[ReleaseArtifactDescriptor]:
    if not artifact_dir.exists():
        raise RuntimeError(f"artifact directory does not exist: {artifact_dir}")
    descriptors: list[ReleaseArtifactDescriptor] = []
    for metadata_path in sorted(artifact_dir.glob("*.release.json")):
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        archive_path_raw = payload.get("archive_path")
        variant = payload.get("variant")
        platform = payload.get("platform")
        arch = payload.get("arch")
        if not all(isinstance(value, str) and value for value in [archive_path_raw, variant, platform, arch]):
            raise RuntimeError(f"invalid release metadata: missing required fields in {metadata_path}")
        archive_path = Path(archive_path_raw)
        if not archive_path.exists():
            raise RuntimeError(f"release archive path does not exist: {archive_path}")
        descriptors.append(_build_release_artifact_descriptor(
            version=version,
            metadata_path=metadata_path,
            payload=payload,
            archive_path=archive_path,
            variant=variant,
            platform=platform,
            arch=arch,
        ))
    if not descriptors:
        raise RuntimeError(f"no release metadata files found in {artifact_dir}")
    _validate_release_artifacts(descriptors)
    return descriptors


def _build_release_artifact_descriptor(
    *,
    version: str,
    metadata_path: Path,
    payload: dict[str, Any],
    archive_path: Path,
    variant: str,
    platform: str,
    arch: str,
) -> ReleaseArtifactDescriptor:
    return ReleaseArtifactDescriptor(
        version=version,
        variant=variant,
        platform=platform,
        arch=arch,
        archive_path=archive_path,
        archive_name=archive_path.name,
        release_metadata_path=metadata_path,
        release_metadata=payload,
        sha256=sha256_file(archive_path),
        size_bytes=archive_path.stat().st_size,
    )


def _validate_release_artifacts(artifacts: list[ReleaseArtifactDescriptor]) -> None:
    seen_variants: set[tuple[str, str, str]] = set()
    for artifact in artifacts:
        current_key = (artifact.platform, artifact.arch, artifact.variant)
        if current_key in seen_variants:
            raise RuntimeError(
                f"duplicate release artifact variant detected: platform={artifact.platform} arch={artifact.arch} "
                f"variant={artifact.variant}"
            )
        seen_variants.add(current_key)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_sha256_file(*, digest: str, filename: str) -> str:
    return f"{digest}  {filename}\n"


def build_version_manifest(
    *,
    version: str,
    channel: str,
    artifacts: list[ReleaseArtifactDescriptor],
    public_base_url: str,
    prefix: str = "",
    published_at: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": VERSION_MANIFEST_SCHEMA_VERSION,
        "channel": channel,
        "version": version,
        "published_at": published_at or datetime.now(tz=timezone.utc).isoformat(),
        "artifacts": {},
    }
    for artifact in sorted(artifacts, key=lambda item: (item.target_key, item.variant)):
        target_artifacts = payload["artifacts"].setdefault(artifact.target_key, {})
        target_artifacts[artifact.variant] = _build_manifest_artifact_entry(
            version=version,
            artifact=artifact,
            public_base_url=public_base_url,
            prefix=prefix,
        )
    return payload


def _build_manifest_artifact_entry(
    *,
    version: str,
    artifact: ReleaseArtifactDescriptor,
    public_base_url: str,
    prefix: str,
) -> dict[str, Any]:
    archive_key = release_object_key(
        version=version,
        filename=artifact.remote_archive_name,
        prefix=prefix,
    )
    sha256_key = release_object_key(version=version, filename=artifact.remote_sha256_name, prefix=prefix)
    metadata_key = release_object_key(
        version=version,
        filename=artifact.remote_release_metadata_name,
        prefix=prefix,
    )
    return {
        "archive_url": public_url_for_key(public_base_url=public_base_url, key=archive_key),
        "sha256_url": public_url_for_key(public_base_url=public_base_url, key=sha256_key),
        "release_metadata_url": public_url_for_key(public_base_url=public_base_url, key=metadata_key),
        "filename": artifact.remote_archive_name,
        "sha256": artifact.sha256,
        "size_bytes": artifact.size_bytes,
    }


def public_url_for_key(*, public_base_url: str, key: str) -> str:
    return f"{public_base_url.rstrip('/')}/{key.lstrip('/')}"


def release_object_key(*, version: str, filename: str, prefix: str = "") -> str:
    base = f"releases/v{version}/{filename}"
    return _join_object_key(prefix, base)


def channel_object_key(*, channel: str, prefix: str = "") -> str:
    return _join_object_key(prefix, f"channels/{channel}.json")


def install_object_key(*, prefix: str = "") -> str:
    return _join_object_key(prefix, "install/install.sh")


def _join_object_key(prefix: str, suffix: str) -> str:
    normalized_prefix = prefix.strip("/")
    normalized_suffix = suffix.strip("/")
    if not normalized_prefix:
        return normalized_suffix
    return f"{normalized_prefix}/{normalized_suffix}"


def build_release_uploads(
    *,
    config: R2PublishConfig,
    version: str,
    artifacts: list[ReleaseArtifactDescriptor],
    installer_body: bytes | None = None,
) -> list[UploadObject]:
    version_manifest = build_version_manifest(
        version=version,
        channel=config.channel,
        artifacts=artifacts,
        public_base_url=config.normalized_public_base_url,
        prefix=config.normalized_prefix,
    )
    version_manifest_body = json.dumps(version_manifest, ensure_ascii=False, indent=2).encode("utf-8")
    uploads = _build_artifact_uploads(
        config=config,
        version=version,
        artifacts=artifacts,
    )
    uploads.extend(
        [
            UploadObject(
                key=release_object_key(
                    version=version,
                    filename="version.json",
                    prefix=config.normalized_prefix,
                ),
                body=version_manifest_body,
                content_type="application/json; charset=utf-8",
                cache_control=no_cache_control(),
            ),
            UploadObject(
                key=channel_object_key(channel=config.channel, prefix=config.normalized_prefix),
                body=version_manifest_body,
                content_type="application/json; charset=utf-8",
                cache_control=no_cache_control(),
            ),
        ]
    )
    if installer_body is not None:
        uploads.append(
            UploadObject(
                key=install_object_key(prefix=config.normalized_prefix),
                body=installer_body,
                content_type="text/x-shellscript; charset=utf-8",
                cache_control=no_cache_control(),
            )
        )
    return uploads


def _build_artifact_uploads(
    *,
    config: R2PublishConfig,
    version: str,
    artifacts: list[ReleaseArtifactDescriptor],
) -> list[UploadObject]:
    uploads: list[UploadObject] = []
    for artifact in artifacts:
        uploads.extend(_build_uploads_for_artifact(
            config=config,
            version=version,
            artifact=artifact,
        ))
    return uploads


def _build_uploads_for_artifact(
    *,
    config: R2PublishConfig,
    version: str,
    artifact: ReleaseArtifactDescriptor,
) -> list[UploadObject]:
    archive_key = release_object_key(
        version=version,
        filename=artifact.remote_archive_name,
        prefix=config.normalized_prefix,
    )
    sha256_key = release_object_key(
        version=version,
        filename=artifact.remote_sha256_name,
        prefix=config.normalized_prefix,
    )
    metadata_key = release_object_key(
        version=version,
        filename=artifact.remote_release_metadata_name,
        prefix=config.normalized_prefix,
    )
    immutable_cache = immutable_cache_control()
    return [
        UploadObject(
            key=archive_key,
            body=artifact.archive_path.read_bytes(),
            content_type=_guess_content_type(artifact.remote_archive_name),
            cache_control=immutable_cache,
        ),
        UploadObject(
            key=sha256_key,
            body=render_sha256_file(digest=artifact.sha256, filename=artifact.remote_archive_name).encode("utf-8"),
            content_type="text/plain; charset=utf-8",
            cache_control=immutable_cache,
        ),
        UploadObject(
            key=metadata_key,
            body=json.dumps(artifact.release_metadata, ensure_ascii=False, indent=2).encode("utf-8"),
            content_type="application/json; charset=utf-8",
            cache_control=immutable_cache,
        ),
    ]


def immutable_cache_control() -> str:
    return "public, max-age=31536000, immutable"


def no_cache_control() -> str:
    return "no-cache"


def _guess_content_type(filename: str) -> str:
    if filename.endswith(".zip"):
        return "application/zip"
    guessed_type, _ = mimetypes.guess_type(filename)
    return guessed_type or "application/octet-stream"
