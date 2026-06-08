from __future__ import annotations

import json
from pathlib import Path

import yaml
from pydantic import ValidationError

from munk.adapters.local_api.app_models import AppUpsertRequest
from munk.services.machine_contracts import InvalidMachineRequestError


def load_app_upsert_request(path: Path) -> AppUpsertRequest:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise InvalidMachineRequestError(f"request file not found: {path}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        try:
            payload = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise InvalidMachineRequestError(f"request file is not valid JSON/YAML: {exc}") from exc
    if not isinstance(payload, dict):
        raise InvalidMachineRequestError("request file must contain an object payload")
    try:
        return AppUpsertRequest.model_validate(payload)
    except ValidationError as exc:
        raise InvalidMachineRequestError(f"request file validation failed: {exc}") from exc
