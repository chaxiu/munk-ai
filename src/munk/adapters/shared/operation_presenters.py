from __future__ import annotations

from munk.adapters.shared.payload_models import OperationSummaryData
from munk.services.operations.models import OperationRecord
from munk.services.operations.payloads import (
    infer_phase,
    infer_platform,
    infer_run_type,
    infer_target_label,
    infer_title,
    source_recording_id,
)


def include_in_run_center(record: OperationRecord) -> bool:
    return infer_run_type(record) is not None


def build_operation_summary(record: OperationRecord) -> OperationSummaryData:
    return OperationSummaryData(
        operation_id=record.operation_id,
        kind=record.kind,
        run_type=infer_run_type(record),
        title=infer_title(record),
        platform=infer_platform(record),
        phase=infer_phase(record),
        target_label=infer_target_label(record),
        source_recording_id=source_recording_id(record),
        status=record.status,
        verification_verdict=record.verification_verdict,
        app_id=record.app_id,
        plan_id=record.plan_id,
        case_id=record.case_id,
        parent_operation_id=record.parent_operation_id,
        batch_id=record.batch_id,
        position_index=record.position_index,
        position_label=record.position_label,
        device_ref=record.device_ref,
        created_at=record.created_at,
        started_at=record.started_at,
        finished_at=record.finished_at,
        error_code=record.error_code,
        error_message=record.error_message,
    )
