from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

VERSION_MANIFEST_SCHEMA_VERSION = "munk.release_manifest.v1"
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
        return f"munk-{self.platform}-{self.arch}-{self.variant}{''.join(self.archive_path.suffixes)}"

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
