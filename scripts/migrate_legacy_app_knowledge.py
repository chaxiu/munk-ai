from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import Any

UPDATED_AT = "2026-06-06T00:00:00Z"
FLOW_TITLES = {
    "下拉刷新",
    "退出登录",
    "重启陌陌app",
}


def _clean(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _card_id(card_type: str, title: str) -> str:
    digest = hashlib.sha1(title.strip().encode("utf-8")).hexdigest()[:10]
    return f"{card_type}-{digest}"


def migrate_legacy_payload(raw: dict[str, Any], *, app_id: str, source_ref: str) -> dict[str, Any]:
    cards: list[dict[str, Any]] = []
    for title, payload in raw.items():
        if not isinstance(payload, dict):
            raise ValueError(f"legacy item must be object: {title}")
        enter = _clean(payload.get("enter"))
        recognize = _clean(payload.get("recognize"))
        card_type = "flow" if title in FLOW_TITLES else "screen"
        card: dict[str, Any] = {
            "card_id": _card_id(card_type, title),
            "app_id": app_id,
            "title": title.strip(),
            "card_type": card_type,
            "status": "active",
            "confidence": 0.9 if card_type == "flow" else 0.95,
            "updated_at": UPDATED_AT,
            "source": {
                "kind": "import",
                "ref": source_ref,
            },
        }
        if card_type == "flow":
            card["payload"] = {
                "goal": recognize or title.strip(),
                "preconditions": [],
                "typical_steps": [enter] if enter else [],
                "completion_signals": [recognize] if recognize else [],
            }
        else:
            card["payload"] = {
                "enter": enter,
                "recognize": recognize,
                "key_elements": [],
                "exit_signals": [],
            }
        cards.append(card)
    return {
        "schema_version": "knowledge.import.v1",
        "app_id": app_id,
        "cards": cards,
    }


def _is_import_document(raw: dict[str, Any]) -> bool:
    return raw.get("schema_version") == "knowledge.import.v1" and isinstance(raw.get("cards"), list)


def _validate_document(path: Path, *, expected_app_id: str) -> dict[str, Any]:
    root = path.parent / "packages" / "shared" / "agent-base" / "src" / "munk" / "app_knowledge"
    package_name = "_migrate_app_knowledge_schema"
    package = types.ModuleType(package_name)
    package.__path__ = [str(root)]
    sys.modules[package_name] = package

    models_spec = importlib.util.spec_from_file_location(f"{package_name}.models", root / "models.py")
    if models_spec is None or models_spec.loader is None:
        raise RuntimeError("failed to load app knowledge models module")
    models_module = importlib.util.module_from_spec(models_spec)
    sys.modules[f"{package_name}.models"] = models_module
    models_spec.loader.exec_module(models_module)

    loader_spec = importlib.util.spec_from_file_location(f"{package_name}.document_loader", root / "document_loader.py")
    if loader_spec is None or loader_spec.loader is None:
        raise RuntimeError("failed to load app knowledge document_loader module")
    loader_module = importlib.util.module_from_spec(loader_spec)
    sys.modules[f"{package_name}.document_loader"] = loader_module
    loader_spec.loader.exec_module(loader_module)

    document = loader_module.validate_app_knowledge_document(path.read_text(encoding="utf-8"), expected_app_id=expected_app_id)
    return {
        "app_id": document.app_id,
        "card_count": len(document.cards),
        "card_types": sorted({card.card_type for card in document.cards}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate legacy app_knowledge.json into knowledge.import.v1 format.")
    parser.add_argument("input_path", type=Path)
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--source-ref", default="app_knowledge.json")
    args = parser.parse_args()

    raw = json.loads(args.input_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("legacy app knowledge must be a JSON object")
    migrated = raw if _is_import_document(raw) else migrate_legacy_payload(raw, app_id=args.app_id, source_ref=args.source_ref)
    args.input_path.write_text(json.dumps(migrated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validation_summary = _validate_document(args.input_path, expected_app_id=args.app_id)
    print(
        json.dumps(
            {
                **validation_summary,
                "flow_titles": [card["title"] for card in migrated["cards"] if card["card_type"] == "flow"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
