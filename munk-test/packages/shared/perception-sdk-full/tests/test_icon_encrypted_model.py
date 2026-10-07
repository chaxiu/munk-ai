from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _load_build_helpers():
    helper_path = PROJECT_DIR / "build_helpers.py"
    module_name = "perception_build_helpers"
    spec = importlib.util.spec_from_file_location(module_name, helper_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_icon_module():
    fake_ort = types.ModuleType("onnxruntime")
    fake_ort.InferenceSession = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    fake_ort.get_available_providers = lambda: ["CPUExecutionProvider"]  # type: ignore[attr-defined]
    sys.modules.setdefault("onnxruntime", fake_ort)
    sys.modules.setdefault("munk_perception_full", types.ModuleType("munk_perception_full"))
    sys.modules["munk_perception_full"].__path__ = [str(SRC_DIR / "munk_perception_full")]  # type: ignore[attr-defined]

    module_name = "munk_perception_full.icon"
    module_path = SRC_DIR / "munk_perception_full" / "icon.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _write_runtime_version_config(config_path: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "python_build_standalone": {
                    "release_tag": "20260414",
                    "python_version": "3.10.20",
                    "archive_flavor": "install_only",
                },
                "android_platform_tools": {"version": "37.0.0"},
                "icon_detect_model": {
                    "manifest_url": "https://downloads.munk.sh/models/detect/detect.json",
                    "name": "detect.onnx",
                    "version": "2026-06-01",
                    "url": "https://downloads.munk.sh/models/detect/detect.onnx",
                    "sha256": "2917650807842f5a7a51d46e142d80f27ea3cdefa9e12bb1fe40d6bfe5ef4b24",
                },
            }
        ),
        encoding="utf-8",
    )


def test_prepare_icon_model_downloads_plaintext_runtime_resource(monkeypatch, tmp_path: Path) -> None:
    helpers = _load_build_helpers()
    config_path = tmp_path / "config" / "build" / "runtime-version.json"
    _write_runtime_version_config(config_path)
    payload_sha256 = hashlib.sha256(b"fake-onnx-payload").hexdigest()
    config_payload = json.loads(config_path.read_text(encoding="utf-8"))
    config_payload["icon_detect_model"]["sha256"] = payload_sha256
    config_path.write_text(json.dumps(config_payload), encoding="utf-8")
    manifest_payload = {
        "name": "detect.onnx",
        "version": "2026-06-01",
        "url": "https://downloads.munk.sh/models/detect/detect.onnx",
        "sha256": payload_sha256,
    }

    def fake_download(url: str) -> bytes:
        if url.endswith(".json"):
            return json.dumps(manifest_payload).encode("utf-8")
        return b"fake-onnx-payload"

    monkeypatch.setattr(helpers, "_download_bytes", fake_download)

    model_path = helpers.prepare_icon_model(tmp_path, version_config_path=config_path)

    assert model_path == tmp_path / "src" / "munk_perception_full" / "resources" / "models" / "detect" / "detect.onnx"
    assert model_path.read_bytes() == b"fake-onnx-payload"


def test_default_runtime_version_config_resolves_from_workspace_root() -> None:
    helpers = _load_build_helpers()

    assert helpers.DEFAULT_RUNTIME_VERSION_CONFIG == Path(__file__).resolve().parents[4] / "config" / "build" / "runtime-version.json"
    assert helpers.DEFAULT_RUNTIME_VERSION_CONFIG.exists()


def test_prepare_icon_model_reuses_existing_resource_without_re_download(monkeypatch, tmp_path: Path) -> None:
    helpers = _load_build_helpers()
    config_path = tmp_path / "config" / "build" / "runtime-version.json"
    _write_runtime_version_config(config_path)
    model_path = helpers.runtime_model_path(tmp_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    existing_model = b"existing-model"
    expected_sha256 = hashlib.sha256(existing_model).hexdigest()
    config_payload = json.loads(config_path.read_text(encoding="utf-8"))
    config_payload["icon_detect_model"]["sha256"] = expected_sha256
    config_payload["icon_detect_model"].pop("manifest_url", None)
    config_path.write_text(json.dumps(config_payload), encoding="utf-8")
    model_path.write_bytes(existing_model)
    download_calls: list[str] = []

    def fake_download(url: str) -> bytes:
        download_calls.append(url)
        return b"new-model"

    monkeypatch.setattr(helpers, "_download_bytes", fake_download)

    prepared = helpers.prepare_icon_model(tmp_path, version_config_path=config_path)

    assert prepared == model_path
    assert prepared.read_bytes() == existing_model
    assert download_calls == []


def test_prepare_icon_model_fails_when_remote_manifest_mismatches_pinned_config(monkeypatch, tmp_path: Path) -> None:
    helpers = _load_build_helpers()
    config_path = tmp_path / "config" / "build" / "runtime-version.json"
    _write_runtime_version_config(config_path)

    def fake_download(url: str) -> bytes:
        if url.endswith(".json"):
            return json.dumps(
                {
                    "name": "detect.onnx",
                    "version": "2026-06-02",
                    "url": "https://downloads.munk.sh/models/detect/detect.onnx",
                    "sha256": "2917650807842f5a7a51d46e142d80f27ea3cdefa9e12bb1fe40d6bfe5ef4b24",
                }
            ).encode("utf-8")
        return b"ignored"

    monkeypatch.setattr(helpers, "_download_bytes", fake_download)

    with pytest.raises(RuntimeError, match="remote icon model manifest does not match pinned runtime version config"):
        helpers.prepare_icon_model(tmp_path, version_config_path=config_path)


def test_load_model_session_keeps_plaintext_path_for_onnx(monkeypatch, tmp_path: Path) -> None:
    icon_module = _load_icon_module()
    plaintext_path = tmp_path / "icon_detect.onnx"
    plaintext_path.write_bytes(b"fake-onnx-payload")
    captured: dict[str, object] = {}

    def fake_session(path_or_bytes, providers=None):  # type: ignore[no-untyped-def]
        captured["payload"] = path_or_bytes
        captured["providers"] = providers
        return "session"

    monkeypatch.setattr(icon_module.ort, "InferenceSession", fake_session)

    session = icon_module._load_model_session(plaintext_path, ["CPUExecutionProvider"])

    assert session == "session"
    assert captured["payload"] == str(plaintext_path)
    assert captured["providers"] == ["CPUExecutionProvider"]
