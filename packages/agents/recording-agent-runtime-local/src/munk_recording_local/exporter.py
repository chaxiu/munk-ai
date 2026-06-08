from __future__ import annotations

from munk.recording import RecordingAnalysisResult, RecordingCaseExport

from .store import RecordingStore


def export_analysis_case(
    store: RecordingStore,
    *,
    recording_id: str,
    analysis: RecordingAnalysisResult,
) -> RecordingCaseExport:
    recording_dir = store.find_recording_dir(recording_id)
    if analysis.test_case is None:
        raise ValueError("analysis result does not contain test_case")
    store.write_analysis_result(recording_dir, analysis)
    store.write_test_case(recording_dir, analysis.test_case.model_dump(mode="json"))
    export_result = RecordingCaseExport(
        recording_id=recording_id,
        case_id=analysis.test_case.case_id,
        case_path=store.test_case_path(recording_dir),
        analysis_path=store.analysis_path(recording_dir),
    )
    store.write_export_manifest(recording_dir, export_result)
    return export_result
