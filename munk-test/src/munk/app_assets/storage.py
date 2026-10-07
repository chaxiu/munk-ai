from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from munk.app_assets.models import AppProfile, normalize_app_id
from munk.paths import assets_root


def _resolve_root_dir(root_dir: Path | None) -> Path:
    return root_dir or assets_root()


class AppRegistry:
    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = _resolve_root_dir(root_dir)
        self.apps_dir = self.root_dir / "apps"

    def list(self) -> list[AppProfile]:
        if not self.apps_dir.exists():
            return []
        items: list[AppProfile] = []
        for app_dir in sorted(path for path in self.apps_dir.iterdir() if path.is_dir()):
            app_yaml = app_dir / "app.yaml"
            if not app_yaml.exists():
                continue
            items.append(self.load(app_dir.name))
        return items

    @staticmethod
    def normalize_app_id(app_id: str) -> str:
        return normalize_app_id(app_id)

    def exists(self, app_id: str) -> bool:
        normalized = self.normalize_app_id(app_id)
        return (self.apps_dir / normalized / "app.yaml").exists()

    def load(self, app_id: str) -> AppProfile:
        normalized = self.normalize_app_id(app_id)
        app_path = self.apps_dir / normalized / "app.yaml"
        if not app_path.exists():
            raise FileNotFoundError(f"AppProfile not found: {app_path}")
        with app_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return AppProfile(**data)

    def save(self, profile: AppProfile) -> None:
        app_id = self.normalize_app_id(profile.app_id)
        app_dir = self.apps_dir / app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        app_path = app_dir / "app.yaml"
        payload = profile.model_copy(update={"app_id": app_id}).model_dump(mode="python", exclude_none=True)
        with app_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)

    def delete(self, app_id: str) -> None:
        normalized = self.normalize_app_id(app_id)
        app_dir = self.apps_dir / normalized
        if app_dir.exists():
            shutil.rmtree(app_dir)

    def introduction_path(self, app_id: str, *, ref: str | None = None) -> Path:
        normalized = self.normalize_app_id(app_id)
        return self.apps_dir / normalized / (ref or "introduction.md")

    def load_introduction(self, app_id: str, *, ref: str | None = None) -> str:
        introduction_path = self.introduction_path(app_id, ref=ref)
        if not introduction_path.exists():
            raise FileNotFoundError(f"App introduction not found: {introduction_path}")
        return introduction_path.read_text(encoding="utf-8").strip()

    def save_introduction(self, app_id: str, content: str, *, ref: str | None = None) -> Path:
        introduction_path = self.introduction_path(app_id, ref=ref)
        introduction_path.parent.mkdir(parents=True, exist_ok=True)
        introduction_path.write_text(content.strip(), encoding="utf-8")
        return introduction_path

    def knowledge_path(self, app_id: str, *, ref: str | None = None) -> Path:
        normalized = self.normalize_app_id(app_id)
        return self.apps_dir / normalized / (ref or "app_knowledge.json")

    def load_knowledge(self, app_id: str, *, ref: str | None = None) -> str:
        knowledge_path = self.knowledge_path(app_id, ref=ref)
        if not knowledge_path.exists():
            raise FileNotFoundError(f"App knowledge not found: {knowledge_path}")
        return knowledge_path.read_text(encoding="utf-8").strip()

    def save_knowledge(self, app_id: str, content: str, *, ref: str | None = None) -> Path:
        knowledge_path = self.knowledge_path(app_id, ref=ref)
        knowledge_path.parent.mkdir(parents=True, exist_ok=True)
        knowledge_path.write_text(content.strip(), encoding="utf-8")
        return knowledge_path
