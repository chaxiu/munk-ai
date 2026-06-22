from __future__ import annotations

import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


def normalize_extracted_root(extract_root: Path) -> Path:
    children = [child for child in extract_root.iterdir() if child.name != "__MACOSX"]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return extract_root


def extract_tar_archive(archive: tarfile.TarFile, destination: Path) -> None:
    # Prefer the safer filter on newer Python, while keeping compatibility with 3.10/3.11.
    try:
        archive.extractall(destination, filter="data")
    except TypeError:
        archive.extractall(destination)


def extract_archive(*, archive_path: Path, destination_dir: Path, temp_prefix: str, error_prefix: str) -> None:
    if destination_dir.exists():
        shutil.rmtree(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=temp_prefix) as temp_dir:
        temp_path = Path(temp_dir)
        if archive_path.name.endswith((".tar.gz", ".tgz")):
            with tarfile.open(archive_path, mode="r:gz") as archive:
                extract_tar_archive(archive, temp_path)
        elif archive_path.name.endswith(".tar.xz"):
            with tarfile.open(archive_path, mode="r:xz") as archive:
                extract_tar_archive(archive, temp_path)
        elif archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(temp_path)
        else:
            raise RuntimeError(f"unsupported {error_prefix} archive format: {archive_path}")
        extracted = normalize_extracted_root(temp_path)
        for child in extracted.iterdir():
            target = destination_dir / child.name
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            shutil.move(str(child), str(target))


def download_with_proxy_support(*, url: str, destination: Path) -> None:
    if curl_available():
        try:
            download_with_curl(url=url, destination=destination)
            return
        except RuntimeError as exc:
            print(f"warning: curl download failed, falling back to urllib: {exc}")
    download_file_with_detected_proxy(url=url, destination=destination)


def curl_available() -> bool:
    return shutil.which("curl") is not None


def download_with_curl(*, url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f"{destination.name}.",
        suffix=".download",
        dir=destination.parent,
        delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)
    command = [
        "curl",
        "--fail",
        "--location",
        "--silent",
        "--show-error",
        "--output",
        str(temp_path),
        url,
    ]
    try:
        subprocess.run(command, check=True, env=os.environ.copy())  # noqa: S603
        temp_path.replace(destination)
    except (OSError, subprocess.CalledProcessError) as exc:
        temp_path.unlink(missing_ok=True)
        raise RuntimeError(f"url={url} error={exc}") from exc


def load_json_with_detected_proxy(url: str) -> object:
    proxies = urllib.request.getproxies_environment()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies))
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "munk-runtime-builder/1.0"},
    )
    try:
        with opener.open(request) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        proxy_summary = format_proxy_summary(proxies)
        raise RuntimeError(f"url={url} proxies={proxy_summary} error={exc}") from exc


def download_file_with_detected_proxy(*, url: str, destination: Path) -> None:
    proxies = urllib.request.getproxies_environment()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies))
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "munk-runtime-builder/1.0"},
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f"{destination.name}.",
        suffix=".download",
        dir=destination.parent,
        delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)
    try:
        with opener.open(request) as response, temp_path.open("wb") as handle:  # noqa: S310
            shutil.copyfileobj(response, handle)
        temp_path.replace(destination)
    except (urllib.error.URLError, OSError) as exc:
        temp_path.unlink(missing_ok=True)
        proxy_summary = format_proxy_summary(proxies)
        raise RuntimeError(f"url={url} proxies={proxy_summary} error={exc}") from exc


def format_proxy_summary(proxies: dict[str, str]) -> str:
    if not proxies:
        return "none"
    return ",".join(f"{scheme}={value}" for scheme, value in sorted(proxies.items()))
