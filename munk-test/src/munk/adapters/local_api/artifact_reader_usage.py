from __future__ import annotations

from typing import cast

from munk.adapters.local_api.response_models import CaseRunArtifactSummaryData
from munk.adapters.shared.payload_models import AttemptTokenUsageData, TokenUsageData
from munk.services.artifact_manifest_models import CaseArtifactEntry
from munk.services.operations.models import OperationRecord
from munk.services.operations.payloads import token_usage_from_result_json


def case_token_usage_by_case_id(record: OperationRecord) -> dict[str, TokenUsageData]:
    if not isinstance(record.result_json, dict):
        return {}
    raw_items = record.result_json.get("items")
    if not isinstance(raw_items, list):
        return {}
    payload: dict[str, TokenUsageData] = {}
    for raw_item in cast(list[object], raw_items):
        if not isinstance(raw_item, dict):
            continue
        item = cast(dict[str, object], raw_item)
        case_id = item.get("case_id")
        token_usage = token_usage_from_result_json(item)
        if isinstance(case_id, str) and case_id and token_usage is not None:
            usage = usage_data_from_payload(token_usage)
            if usage is not None:
                payload[case_id] = usage
    return payload


def build_case_run_artifact_summary(
    case_run: CaseArtifactEntry,
    case_usage_by_case_id: dict[str, TokenUsageData],
) -> CaseRunArtifactSummaryData:
    token_usage = case_usage_by_case_id.get(case_run.case_id)
    return CaseRunArtifactSummaryData(
        case_id=case_run.case_id,
        title=case_run.title,
        operation_id=case_run.operation_id,
        verdict=case_run.verdict,
        execution_status=case_run.execution_status,
        run_dir=str(case_run.run_dir),
        token_usage=token_usage,
    )


def usage_data_from_payload(payload: object) -> TokenUsageData | None:
    if not isinstance(payload, dict):
        return None
    try:
        return TokenUsageData.model_validate(payload)
    except Exception:
        return None


def attempt_usage_data_list(payload: object) -> list[AttemptTokenUsageData]:
    if not isinstance(payload, list):
        return []
    items: list[AttemptTokenUsageData] = []
    for raw_item in cast(list[object], payload):
        if not isinstance(raw_item, dict):
            continue
        item = cast(dict[str, object], raw_item)
        try:
            items.append(AttemptTokenUsageData.model_validate(item))
        except Exception:
            continue
    return items
