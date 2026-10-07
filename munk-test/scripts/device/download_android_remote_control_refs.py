#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

USER_AGENT = "ai-monkey-reference-downloader/1.0"


@dataclass(frozen=True)
class RepoSpec:
    slug: str
    ref: str = "HEAD"
    notes: str = ""

    @property
    def name(self) -> str:
        return self.slug.split("/", 1)[1]

    @property
    def download_url(self) -> str:
        return f"https://codeload.github.com/{self.slug}/zip/{self.ref}"


DEFAULT_REPOS: tuple[RepoSpec, ...] = (
    RepoSpec(
        slug="NetrisTV/ws-scrcpy",
        ref="master",
        notes="Classic browser-side scrcpy control implementation with touch events.",
    ),
    RepoSpec(
        slug="gjovanov/scws",
        ref="main",
        notes="Modern scrcpy-via-WebSocket project using Tango and browser remote control.",
    ),
    RepoSpec(
        slug="ccizm/WebScrcpy-MobileAgent",
        ref="main",
        notes="Recent browser mirroring/control project with drag and touch support.",
    ),
    RepoSpec(
        slug="bonelag/ScrcpyWeb",
        ref="main",
        notes="Web scrcpy implementation for additional UI/control reference.",
    ),
    RepoSpec(
        slug="yume-chan/leap-scrcpy",
        ref="main",
        notes="Tango ecosystem project with continuous pointer and input handling ideas.",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download representative open-source Android remote-control references "
            "into a local directory for offline code analysis."
        )
    )
    parser.add_argument(
        "--output-dir",
        default="tmp/reference_repos/android_remote_control",
        help="Directory to place extracted repositories.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete any existing target repository directories before downloading.",
    )
    parser.add_argument(
        "--repo",
        action="append",
        default=[],
        metavar="OWNER/REPO[@REF]",
        help=(
            "Additional repository to download. Can be repeated. "
            "Format: owner/repo or owner/repo@branch-or-tag."
        ),
    )
    return parser.parse_args()


def parse_repo_arg(raw: str) -> RepoSpec:
    if "@" in raw:
        slug, ref = raw.split("@", 1)
    else:
        slug, ref = raw, "main"
    if "/" not in slug:
        raise ValueError(f"Invalid repo value: {raw!r}")
    return RepoSpec(slug=slug, ref=ref)


def build_repo_list(extra_repos: list[str]) -> list[RepoSpec]:
    repos = list(DEFAULT_REPOS)
    for raw in extra_repos:
        repos.append(parse_repo_arg(raw))
    return repos


def ensure_clean_dir(path: Path, force: bool) -> None:
    if path.exists():
        if not force:
            raise FileExistsError(f"Target path already exists: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def download_zip(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    opener = build_opener()
    with opener.open(request, timeout=60) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def extract_zip(archive_path: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        root_prefix = None
        for member in members:
            parts = Path(member.filename).parts
            if not parts:
                continue
            root_prefix = parts[0]
            break
        if root_prefix is None:
            raise RuntimeError(f"Archive is empty: {archive_path}")

        temp_extract_dir = destination.parent / f".extract-{destination.name}"
        if temp_extract_dir.exists():
            shutil.rmtree(temp_extract_dir)
        temp_extract_dir.mkdir(parents=True, exist_ok=True)
        try:
            archive.extractall(temp_extract_dir)
            extracted_root = temp_extract_dir / root_prefix
            if not extracted_root.exists():
                raise RuntimeError(f"Unexpected archive layout in {archive_path}")
            shutil.move(str(extracted_root), str(destination))
        finally:
            shutil.rmtree(temp_extract_dir, ignore_errors=True)


def detect_primary_paths(repo_dir: Path) -> dict[str, str]:
    candidates = {
        "readme": ["README.md", "readme.md"],
        "package_json": ["package.json"],
        "src_dir": ["src", "packages", "ui", "web"],
    }
    result: dict[str, str] = {}
    for key, names in candidates.items():
        for name in names:
            path = repo_dir / name
            if path.exists():
                result[key] = str(path.relative_to(repo_dir))
                break
    return result


def write_manifest(output_dir: Path, repos: list[RepoSpec]) -> Path:
    manifest_path = output_dir / "manifest.json"
    entries = []
    for repo in repos:
        repo_dir = output_dir / repo.name
        entries.append(
            {
                **asdict(repo),
                "download_url": repo.download_url,
                "local_dir": str(repo_dir),
                "primary_paths": detect_primary_paths(repo_dir) if repo_dir.exists() else {},
            }
        )
    manifest_path.write_text(json.dumps({"repos": entries}, indent=2), encoding="utf-8")
    return manifest_path


def download_repo(repo: RepoSpec, output_dir: Path, force: bool) -> None:
    repo_dir = output_dir / repo.name
    ensure_clean_dir(repo_dir, force=force)
    with tempfile.TemporaryDirectory(prefix=f"{repo.name}-") as tmp_dir:
        archive_path = Path(tmp_dir) / f"{repo.name}.zip"
        download_zip(repo.download_url, archive_path)
        shutil.rmtree(repo_dir)
        extract_zip(archive_path, repo_dir)


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    repos = build_repo_list(args.repo)

    failures: list[dict[str, str]] = []
    for repo in repos:
        print(f"[download] {repo.slug}@{repo.ref}")
        try:
            download_repo(repo, output_dir, force=args.force)
        except FileExistsError as error:
            print(f"[skip] {error}", file=sys.stderr)
            failures.append({"repo": repo.slug, "error": str(error)})
        except HTTPError as error:
            message = f"HTTP {error.code} while downloading {repo.download_url}"
            print(f"[error] {message}", file=sys.stderr)
            failures.append({"repo": repo.slug, "error": message})
        except URLError as error:
            message = f"Network error for {repo.download_url}: {error.reason}"
            print(f"[error] {message}", file=sys.stderr)
            failures.append({"repo": repo.slug, "error": message})
        except Exception as error:  # pragma: no cover - defensive boundary
            message = f"Unexpected failure for {repo.slug}: {error}"
            print(f"[error] {message}", file=sys.stderr)
            failures.append({"repo": repo.slug, "error": message})

    manifest_path = write_manifest(output_dir, repos)
    print(f"[manifest] {manifest_path}")
    if failures:
        print(json.dumps({"failures": failures}, indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
