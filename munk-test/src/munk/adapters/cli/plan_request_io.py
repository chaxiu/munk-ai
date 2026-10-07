from __future__ import annotations

import json
from pathlib import Path

import yaml
from pydantic import ValidationError

from munk.adapters.local_api.plan_models import CaseUpsertRequest, PlanCaseReorderRequest
from munk.services.machine_contracts import InvalidMachineRequestError


def _load_object_payload(path: Path) -> dict[str, object]:
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
    return payload


def load_case_upsert_request(path: Path) -> CaseUpsertRequest:
    payload = _load_object_payload(path)
    try:
        return CaseUpsertRequest.model_validate(payload)
    except ValidationError as exc:
        raise InvalidMachineRequestError(f"request file validation failed: {exc}") from exc


def load_case_reorder_request(path: Path) -> PlanCaseReorderRequest:
    payload = _load_object_payload(path)
    try:
        return PlanCaseReorderRequest.model_validate(payload)
    except ValidationError as exc:
        raise InvalidMachineRequestError(f"request file validation failed: {exc}") from exc
