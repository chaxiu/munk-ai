from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION_MANIFEST_SCHEMA_VERSION = "munk.release_manifest.v1"
PROJECT_VERSION_PATTERN = re.compile(r'^\s*version\s*=\s*"([^"]+)"\s*$')
MACOS_PLATFORM_KEY = "darwin"


@dataclass(frozen=True)
class R2PublishConfig:
    account_id: str
    access_key_id: str
    secret_access_key: str
    bucket_name: str
    public_base_url: str
    region: str = "auto"
    channel: str = "stable"
    prefix: str = ""

    @property
    def endpoint(self) -> str:
        return f"https://{self.account_id}.r2.cloudflarestorage.com"

    @property
    def normalized_public_base_url(self) -> str:
        return self.public_base_url.rstrip("/")

    @property
    def normalized_prefix(self) -> str:
        return self.prefix.strip("/")


@dataclass(frozen=True)
class ReleaseArtifactDescriptor:
    version: str
    variant: str
    platform: str
    arch: str
    archive_path: Path
    archive_name: str
    release_metadata_path: Path
    release_metadata: dict[str, Any]
    sha256: str
    size_bytes: int

    @property
    def platform_key(self) -> str:
        if self.platform == "macos":
            return MACOS_PLATFORM_KEY
        return self.platform

    @property
    def target_key(self) -> str:
        return f"{self.platform_key}-{self.arch}"

    @property
    def remote_archive_name(self) -> str:
        return f"munk-{self.platform}-{self.arch}-{self.variant}{self.archive_path.suffix}"

    @property
    def remote_release_metadata_name(self) -> str:
        return f"munk-{self.platform}-{self.arch}-{self.variant}.release.json"

    @property
    def remote_sha256_name(self) -> str:
        return f"{self.remote_archive_name}.sha256"


@dataclass(frozen=True)
class UploadObject:
    key: str
    body: bytes
    content_type: str
    cache_control: str


def load_publish_config(config_path: Path) -> R2PublishConfig:
    payload = _parse_env_file(config_path)
    required_keys = [
        "R2_ACCOUNT_ID",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET_NAME",
        "R2_PUBLIC_BASE_URL",
    ]
    missing = [key for key in required_keys if not payload.get(key)]
    if missing:
        raise RuntimeError(f"missing R2 publish settings in {config_path}: {', '.join(missing)}")
    return R2PublishConfig(
        account_id=payload["R2_ACCOUNT_ID"],
        access_key_id=payload["R2_ACCESS_KEY_ID"],
        secret_access_key=payload["R2_SECRET_ACCESS_KEY"],
        bucket_name=payload["R2_BUCKET_NAME"],
        public_base_url=payload["R2_PUBLIC_BASE_URL"],
        region=payload.get("R2_REGION", "auto") or "auto",
        channel=payload.get("R2_CHANNEL", "stable") or "stable",
        prefix=payload.get("R2_PREFIX", ""),
    )


def load_release_version(project_root: Path) -> str:
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        raise RuntimeError(f"missing pyproject.toml: {pyproject_path}")
    in_project_section = False
    for raw_line in pyproject_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("["):
            in_project_section = line == "[project]"
            continue
        if not in_project_section:
            continue
        match = PROJECT_VERSION_PATTERN.match(raw_line)
        if match is not None:
            return match.group(1)
    raise RuntimeError(f"missing [project].version in {pyproject_path}")


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
        sha256 = sha256_file(archive_path)
        size_bytes = archive_path.stat().st_size
        descriptors.append(
            ReleaseArtifactDescriptor(
                version=version,
                variant=variant,
                platform=platform,
                arch=arch,
                archive_path=archive_path,
                archive_name=archive_path.name,
                release_metadata_path=metadata_path,
                release_metadata=payload,
                sha256=sha256,
                size_bytes=size_bytes,
            )
        )
    if not descriptors:
        raise RuntimeError(f"no release metadata files found in {artifact_dir}")
    _validate_release_artifacts(descriptors)
    return descriptors


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
        target_artifacts[artifact.variant] = {
            "archive_url": public_url_for_key(public_base_url=public_base_url, key=archive_key),
            "sha256_url": public_url_for_key(public_base_url=public_base_url, key=sha256_key),
            "release_metadata_url": public_url_for_key(public_base_url=public_base_url, key=metadata_key),
            "filename": artifact.remote_archive_name,
            "sha256": artifact.sha256,
            "size_bytes": artifact.size_bytes,
        }
    return payload


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
    uploads: list[UploadObject] = []
    for artifact in artifacts:
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
        uploads.extend(
            [
                UploadObject(
                    key=archive_key,
                    body=artifact.archive_path.read_bytes(),
                    content_type=_guess_content_type(artifact.remote_archive_name),
                    cache_control=immutable_cache_control(),
                ),
                UploadObject(
                    key=sha256_key,
                    body=render_sha256_file(digest=artifact.sha256, filename=artifact.remote_archive_name).encode("utf-8"),
                    content_type="text/plain; charset=utf-8",
                    cache_control=immutable_cache_control(),
                ),
                UploadObject(
                    key=metadata_key,
                    body=json.dumps(artifact.release_metadata, ensure_ascii=False, indent=2).encode("utf-8"),
                    content_type="application/json; charset=utf-8",
                    cache_control=immutable_cache_control(),
                ),
            ]
        )
    version_key = release_object_key(version=version, filename="version.json", prefix=config.normalized_prefix)
    uploads.append(
        UploadObject(
            key=version_key,
            body=version_manifest_body,
            content_type="application/json; charset=utf-8",
            cache_control=no_cache_control(),
        )
    )
    uploads.append(
        UploadObject(
            key=channel_object_key(channel=config.channel, prefix=config.normalized_prefix),
            body=version_manifest_body,
            content_type="application/json; charset=utf-8",
            cache_control=no_cache_control(),
        )
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


def immutable_cache_control() -> str:
    return "public, max-age=31536000, immutable"


def no_cache_control() -> str:
    return "no-cache"


def _guess_content_type(filename: str) -> str:
    if filename.endswith(".zip"):
        return "application/zip"
    guessed_type, _ = mimetypes.guess_type(filename)
    return guessed_type or "application/octet-stream"


def upload_object(*, config: R2PublishConfig, upload: UploadObject) -> None:
    timestamp = datetime.now(tz=timezone.utc)
    request = build_signed_put_request(
        config=config,
        key=upload.key,
        body=upload.body,
        content_type=upload.content_type,
        cache_control=upload.cache_control,
        timestamp=timestamp,
    )
    try:
        with urllib.request.urlopen(request) as response:  # noqa: S310
            status_code = getattr(response, "status", None)
            if status_code not in {200, 201}:
                raise RuntimeError(f"unexpected upload status for {upload.key}: {status_code}")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"failed to upload R2 object {upload.key}: {exc}") from exc


def build_signed_put_request(
    *,
    config: R2PublishConfig,
    key: str,
    body: bytes,
    content_type: str,
    cache_control: str,
    timestamp: datetime,
) -> urllib.request.Request:
    canonical_path = "/" + "/".join(
        urllib.parse.quote(part, safe="") for part in [config.bucket_name, *key.strip("/").split("/")]
    )
    amz_date = timestamp.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = timestamp.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(body).hexdigest()
    host = urllib.parse.urlparse(config.endpoint).netloc
    canonical_headers = (
        f"cache-control:{cache_control}\n"
        f"content-type:{content_type}\n"
        f"host:{host}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "cache-control;content-type;host;x-amz-content-sha256;x-amz-date"
    canonical_request = "\n".join(
        [
            "PUT",
            canonical_path,
            "",
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )
    credential_scope = f"{date_stamp}/{config.region}/s3/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    signing_key = _derive_signing_key(config.secret_access_key, date_stamp, config.region, "s3")
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        "AWS4-HMAC-SHA256 "
        f"Credential={config.access_key_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )
    request = urllib.request.Request(
        url=f"{config.endpoint}{canonical_path}",
        data=body,
        method="PUT",
        headers={
            "Authorization": authorization,
            "Cache-Control": cache_control,
            "Content-Length": str(len(body)),
            "Content-Type": content_type,
            "Host": host,
            "X-Amz-Content-SHA256": payload_hash,
            "X-Amz-Date": amz_date,
        },
    )
    return request


def _derive_signing_key(secret_access_key: str, date_stamp: str, region: str, service: str) -> bytes:
    key_date = _sign_bytes(("AWS4" + secret_access_key).encode("utf-8"), date_stamp)
    key_region = _sign_bytes(key_date, region)
    key_service = _sign_bytes(key_region, service)
    return _sign_bytes(key_service, "aws4_request")


def _sign_bytes(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise RuntimeError(f"missing config file: {path}")
    payload: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        payload[key.strip()] = _strip_shell_quotes(value.strip())
    return payload


def _strip_shell_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value
