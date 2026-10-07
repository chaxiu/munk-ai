from __future__ import annotations

import json
from pathlib import Path

import cv2
from munk.app import AppTarget
from munk.recording import (
    ForwardingEvent,
    LiveViewFrame,
    ObservationSnapshot,
    RecordedInputEvent,
    RecordingAnalysisResult,
    RecordingAssetManifest,
    RecordingCaseExport,
    RecordingReplayResult,
    RecordingSession,
    RecordingSessionNotFoundError,
    TimelineEntry,
)
from munk.testing import TestCase

from .paths import allocate_recording_dir, recording_assets_home


class RecordingStore:
    def find_recording_dir(self, recording_id: str) -> Path:
        root = recording_assets_home()
        if not root.exists():
            raise RecordingSessionNotFoundError(f"recording session '{recording_id}' was not found")
        for app_dir in root.iterdir():
            if not app_dir.is_dir():
                continue
            candidate = app_dir / recording_id
            if candidate.is_dir():
                return candidate
        raise RecordingSessionNotFoundError(f"recording session '{recording_id}' was not found")

    def create_session(
        self,
        *,
        app_target: AppTarget,
        device_ref: str | None,
        case_id: str | None,
    ) -> RecordingSession:
        recording_id, recording_dir = allocate_recording_dir(app_id=app_target.app_id)
        live_dir = recording_dir / "live"
        frames_dir = recording_dir / "frames"
        events_dir = recording_dir / "events"
        evidence_dir = recording_dir / "evidence"
        timeline_dir = recording_dir / "timeline"
        observations_dir = recording_dir / "observations"
        live_dir.mkdir(parents=True, exist_ok=True)
        frames_dir.mkdir(parents=True, exist_ok=True)
        events_dir.mkdir(parents=True, exist_ok=True)
        evidence_dir.mkdir(parents=True, exist_ok=True)
        timeline_dir.mkdir(parents=True, exist_ok=True)
        observations_dir.mkdir(parents=True, exist_ok=True)

        session = RecordingSession(
            recording_id=recording_id,
            app_id=app_target.app_id,
            app_target=app_target,
            case_id=case_id,
            device_ref=device_ref,
            status="created",
            asset_dir=recording_dir,
        )
        manifest = RecordingAssetManifest(
            recording_id=recording_id,
            session_path=self.session_path(recording_dir),
        )
        self.write_session(session)
        self.write_manifest(manifest)
        return session

    def read_session(self, recording_dir: Path) -> RecordingSession:
        payload = json.loads(self.session_path(recording_dir).read_text(encoding="utf-8"))
        return RecordingSession.model_validate(payload)

    def write_session(self, session: RecordingSession) -> None:
        self._write_json(self.session_path(session.asset_dir), session.model_dump(mode="json"))

    def read_manifest(self, recording_dir: Path) -> RecordingAssetManifest:
        payload = json.loads(self.manifest_path(recording_dir).read_text(encoding="utf-8"))
        return RecordingAssetManifest.model_validate(payload)

    def write_manifest(self, manifest: RecordingAssetManifest) -> None:
        self._write_json(self.manifest_path(manifest.session_path.parent), manifest.model_dump(mode="json"))

    def write_frame(self, session: RecordingSession, frame: LiveViewFrame, image) -> RecordingAssetManifest:  # noqa: ANN001
        recording_dir = session.asset_dir
        frame_image_path = self.frame_image_path(recording_dir, frame.seq)
        frame_meta_path = self.frame_meta_path(recording_dir, frame.seq)
        current_image_path = self.current_image_path(recording_dir)
        current_meta_path = self.current_meta_path(recording_dir)

        cv2.imwrite(str(frame_image_path), image)
        cv2.imwrite(str(current_image_path), image)
        self._write_json(frame_meta_path, frame.model_dump(mode="json"))
        self._write_json(current_meta_path, frame.model_dump(mode="json"))

        manifest = self.read_manifest(recording_dir)
        manifest.current_frame_path = current_image_path
        manifest.frame_count = max(manifest.frame_count, frame.seq)
        manifest.latest_frame_seq = frame.seq
        manifest.generated_files = {
            "session": str(self.session_path(recording_dir)),
            "manifest": str(self.manifest_path(recording_dir)),
            "current_image": str(current_image_path),
            "current_metadata": str(current_meta_path),
            "latest_frame_image": str(frame_image_path),
            "latest_frame_metadata": str(frame_meta_path),
        }
        self.write_manifest(manifest)
        return manifest

    def read_events(self, recording_dir: Path) -> list[RecordedInputEvent]:
        path = self.recording_events_path(recording_dir)
        if not path.exists():
            return []
        events: list[RecordedInputEvent] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            events.append(RecordedInputEvent.model_validate_json(line))
        return events

    def append_event(self, session: RecordingSession, event: RecordedInputEvent) -> RecordingAssetManifest:
        return self.append_recording_event(session, event)

    def append_recording_event(
        self,
        session: RecordingSession,
        event: RecordedInputEvent,
    ) -> RecordingAssetManifest:
        path = self.recording_events_path(session.asset_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json())
            handle.write("\n")
        manifest = self.read_manifest(session.asset_dir)
        manifest.event_count += 1
        manifest.generated_files = {
            **manifest.generated_files,
            "recording_events": str(path),
        }
        self.write_manifest(manifest)
        return manifest

    def read_forwarding_events(self, recording_dir: Path) -> list[ForwardingEvent]:
        path = self.forwarding_events_path(recording_dir)
        if not path.exists():
            return []
        events: list[ForwardingEvent] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            events.append(ForwardingEvent.model_validate_json(line))
        return events

    def append_forwarding_event(
        self,
        session: RecordingSession,
        event: ForwardingEvent,
    ) -> RecordingAssetManifest:
        path = self.forwarding_events_path(session.asset_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json())
            handle.write("\n")
        manifest = self.read_manifest(session.asset_dir)
        manifest.generated_files = {
            **manifest.generated_files,
            "forwarding_events": str(path),
        }
        self.write_manifest(manifest)
        return manifest

    def read_timeline(self, recording_dir: Path) -> list[TimelineEntry]:
        path = self.timeline_path(recording_dir)
        if not path.exists():
            return []
        entries: list[TimelineEntry] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entries.append(TimelineEntry.model_validate_json(line))
        return entries

    def append_timeline_entry(
        self,
        session: RecordingSession,
        entry: TimelineEntry,
    ) -> RecordingAssetManifest:
        path = self.timeline_path(session.asset_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(entry.model_dump_json())
            handle.write("\n")
        manifest = self.read_manifest(session.asset_dir)
        manifest.timeline_count += 1
        manifest.latest_timeline_entry_id = entry.entry_id
        manifest.generated_files = {
            **manifest.generated_files,
            "timeline": str(path),
        }
        self.write_manifest(manifest)
        return manifest

    def write_observation(
        self,
        session: RecordingSession,
        observation: ObservationSnapshot,
        image,  # noqa: ANN001
        metadata: dict[str, object],
        ui_tree_text: str | None,
    ) -> RecordingAssetManifest:
        observation_dir = self.observation_dir(session.asset_dir, observation.observation_id)
        observation_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(observation.image_path), image)
        self._write_json(observation.metadata_path, metadata)
        if ui_tree_text is not None:
            observation.ui_tree_path.parent.mkdir(parents=True, exist_ok=True) if observation.ui_tree_path else None
            if observation.ui_tree_path is not None:
                observation.ui_tree_path.write_text(ui_tree_text, encoding="utf-8")
        manifest = self.read_manifest(session.asset_dir)
        manifest.observation_count += 1
        manifest.latest_observation_id = observation.observation_id
        manifest.generated_files = {
            **manifest.generated_files,
            "observations_root": str(self.observations_dir(session.asset_dir)),
        }
        self.write_manifest(manifest)
        return manifest

    def read_observation(self, recording_dir: Path, observation_id: str) -> ObservationSnapshot:
        metadata_path = self.observation_meta_path(recording_dir, observation_id)
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        return ObservationSnapshot.model_validate(payload)

    def read_observation_metadata(self, recording_dir: Path, observation_id: str) -> dict[str, object]:
        metadata_path = self.observation_meta_path(recording_dir, observation_id)
        return json.loads(metadata_path.read_text(encoding="utf-8"))

    def read_observation_tree_text(self, recording_dir: Path, observation_id: str) -> str | None:
        tree_path = self.observation_tree_path(recording_dir, observation_id)
        if not tree_path.exists():
            return None
        return tree_path.read_text(encoding="utf-8")

    def write_tap_evidence(
        self,
        session: RecordingSession,
        event: RecordedInputEvent,
        image,  # noqa: ANN001
        metadata: dict[str, object],
    ) -> RecordingAssetManifest:
        image_path = self.tap_evidence_image_path(session.asset_dir, event.event_id)
        metadata_path = self.tap_evidence_meta_path(session.asset_dir, event.event_id)
        cv2.imwrite(str(image_path), image)
        self._write_json(metadata_path, metadata)
        manifest = self.read_manifest(session.asset_dir)
        manifest.generated_files = {
            **manifest.generated_files,
            f"{event.event_id}_image": str(image_path),
            f"{event.event_id}_metadata": str(metadata_path),
        }
        self.write_manifest(manifest)
        return manifest

    def read_analysis_result(self, recording_dir: Path) -> RecordingAnalysisResult | None:
        path = self.analysis_path(recording_dir)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return RecordingAnalysisResult.model_validate(payload)

    def write_analysis_result(
        self,
        recording_dir: Path,
        analysis: RecordingAnalysisResult,
    ) -> None:
        self._write_json(self.analysis_path(recording_dir), analysis.model_dump(mode="json"))

    def write_test_case(self, recording_dir: Path, test_case: dict[str, object]) -> None:
        self._write_json(self.test_case_path(recording_dir), test_case)

    def write_export_manifest(self, recording_dir: Path, export_result: RecordingCaseExport) -> None:
        self._write_json(self.export_manifest_path(recording_dir), export_result.model_dump(mode="json"))

    def read_export_manifest(self, recording_dir: Path) -> RecordingCaseExport | None:
        path = self.export_manifest_path(recording_dir)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return RecordingCaseExport.model_validate(payload)

    def read_test_case(self, recording_dir: Path) -> TestCase | None:
        path = self.test_case_path(recording_dir)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return TestCase.model_validate(payload)

    def write_replay_manifest(self, recording_dir: Path, replay_result: RecordingReplayResult) -> None:
        self._write_json(self.replay_manifest_path(recording_dir), replay_result.model_dump(mode="json"))

    def read_replay_manifest(self, recording_dir: Path) -> RecordingReplayResult | None:
        path = self.replay_manifest_path(recording_dir)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return RecordingReplayResult.model_validate(payload)

    @staticmethod
    def session_path(recording_dir: Path) -> Path:
        return recording_dir / "session.json"

    @staticmethod
    def manifest_path(recording_dir: Path) -> Path:
        return recording_dir / "manifest.json"

    @staticmethod
    def current_image_path(recording_dir: Path) -> Path:
        return recording_dir / "live" / "current.png"

    @staticmethod
    def current_meta_path(recording_dir: Path) -> Path:
        return recording_dir / "live" / "current.json"

    @staticmethod
    def frame_image_path(recording_dir: Path, seq: int) -> Path:
        return recording_dir / "frames" / f"frame_{seq:06d}.png"

    @staticmethod
    def frame_meta_path(recording_dir: Path, seq: int) -> Path:
        return recording_dir / "frames" / f"frame_{seq:06d}.json"

    @staticmethod
    def events_path(recording_dir: Path) -> Path:
        return RecordingStore.recording_events_path(recording_dir)

    @staticmethod
    def recording_events_path(recording_dir: Path) -> Path:
        return recording_dir / "events" / "recording.jsonl"

    @staticmethod
    def forwarding_events_path(recording_dir: Path) -> Path:
        return recording_dir / "events" / "forwarding.jsonl"

    @staticmethod
    def timeline_path(recording_dir: Path) -> Path:
        return recording_dir / "timeline" / "timeline.jsonl"

    @staticmethod
    def observations_dir(recording_dir: Path) -> Path:
        return recording_dir / "observations"

    @staticmethod
    def observation_dir(recording_dir: Path, observation_id: str) -> Path:
        return RecordingStore.observations_dir(recording_dir) / observation_id

    @staticmethod
    def observation_image_path(recording_dir: Path, observation_id: str) -> Path:
        return RecordingStore.observation_dir(recording_dir, observation_id) / "screen.png"

    @staticmethod
    def observation_meta_path(recording_dir: Path, observation_id: str) -> Path:
        return RecordingStore.observation_dir(recording_dir, observation_id) / "meta.json"

    @staticmethod
    def observation_tree_path(recording_dir: Path, observation_id: str) -> Path:
        return RecordingStore.observation_dir(recording_dir, observation_id) / "tree.xml"

    @staticmethod
    def tap_evidence_image_path(recording_dir: Path, event_id: str) -> Path:
        return recording_dir / "evidence" / f"{event_id}_after.png"

    @staticmethod
    def tap_evidence_meta_path(recording_dir: Path, event_id: str) -> Path:
        return recording_dir / "evidence" / f"{event_id}_after.json"

    @staticmethod
    def case_dir(recording_dir: Path) -> Path:
        return recording_dir / "case"

    @staticmethod
    def analysis_path(recording_dir: Path) -> Path:
        return RecordingStore.case_dir(recording_dir) / "analysis.json"

    @staticmethod
    def test_case_path(recording_dir: Path) -> Path:
        return RecordingStore.case_dir(recording_dir) / "test_case.json"

    @staticmethod
    def export_manifest_path(recording_dir: Path) -> Path:
        return RecordingStore.case_dir(recording_dir) / "export_manifest.json"

    @staticmethod
    def replay_manifest_path(recording_dir: Path) -> Path:
        return RecordingStore.case_dir(recording_dir) / "replay_manifest.json"

    @staticmethod
    def _write_json(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
