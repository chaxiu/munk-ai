from __future__ import annotations

import hashlib
from dataclasses import dataclass
from threading import Event
from time import monotonic
from typing import Any, cast

from munk.recording import (
    LiveViewFrame,
    ObservationSnapshot,
    RecordedCurrentAppState,
    RecordingAssetManifest,
    RecordingSession,
)

from .android_backend import AndroidRecordingBackend
from .store import RecordingStore


@dataclass
class ObservationCaptureCoordinator:
    store: RecordingStore
    stabilization_interval_seconds: float
    stabilization_timeout_seconds: float

    def capture_frame(
        self,
        *,
        session: RecordingSession,
        backend: AndroidRecordingBackend,
        seq: int,
    ) -> LiveViewFrame:
        image = backend.screenshot_bgr()
        current = backend.app_current()
        frame = LiveViewFrame(
            recording_id=session.recording_id,
            seq=seq,
            image_path=self.store.frame_image_path(session.asset_dir, seq),
            width=int(image.shape[1]),
            height=int(image.shape[0]),
            entry_identity=current.entry_identity,
            activity_name=current.activity_name,
        )
        self.store.write_frame(session, frame, image)
        return frame

    def capture_stable_after_observation(
        self,
        *,
        session: RecordingSession,
        backend: AndroidRecordingBackend,
        latest_manifest: RecordingAssetManifest | None,
        latest_frame_seq: int | None,
        stop_event: Event | None,
    ) -> ObservationSnapshot:
        deadline = monotonic() + self.stabilization_timeout_seconds
        last_candidate: ObservationCandidate | None = None
        stable_hits = 0
        while True:
            candidate = self._capture_observation_candidate(backend=backend)
            if last_candidate is not None and candidate.observation_hash == last_candidate.observation_hash:
                stable_hits += 1
            else:
                stable_hits = 1
            last_candidate = candidate
            if stable_hits >= 2:
                return self._persist_observation_from_candidate(
                    session=session,
                    candidate=candidate,
                    observation_id=self.next_observation_id(latest_manifest),
                    frame_seq=latest_frame_seq,
                    stabilized=True,
                )
            if monotonic() >= deadline:
                return self._persist_observation_from_candidate(
                    session=session,
                    candidate=candidate,
                    observation_id=self.next_observation_id(latest_manifest),
                    frame_seq=latest_frame_seq,
                    stabilized=False,
                )
            if stop_event is not None:
                stop_event.wait(self.stabilization_interval_seconds)

    def persist_observation(
        self,
        *,
        session: RecordingSession,
        backend: AndroidRecordingBackend,
        observation_id: str,
        frame_seq: int | None,
        stabilized: bool,
    ) -> ObservationSnapshot:
        candidate = self._capture_observation_candidate(backend=backend)
        return self._persist_observation_from_candidate(
            session=session,
            candidate=candidate,
            observation_id=observation_id,
            frame_seq=frame_seq,
            stabilized=stabilized,
        )

    @staticmethod
    def next_observation_id(latest_manifest: RecordingAssetManifest | None) -> str:
        next_index = (latest_manifest.observation_count if latest_manifest is not None else 0) + 1
        return f"obs_{next_index:06d}"

    def _persist_observation_from_candidate(
        self,
        *,
        session: RecordingSession,
        candidate: "ObservationCandidate",
        observation_id: str,
        frame_seq: int | None,
        stabilized: bool,
    ) -> ObservationSnapshot:
        observation = ObservationSnapshot(
            observation_id=observation_id,
            recording_id=session.recording_id,
            image_path=self.store.observation_image_path(session.asset_dir, observation_id),
            metadata_path=self.store.observation_meta_path(session.asset_dir, observation_id),
            ui_tree_path=self.store.observation_tree_path(session.asset_dir, observation_id)
            if candidate.ui_tree_text is not None
            else None,
            entry_identity=candidate.entry_identity,
            surface_identity=candidate.surface_identity,
            current_app_state=candidate.current_app_state,
            frame_seq=frame_seq,
            tree_available=candidate.ui_tree_text is not None,
            ui_tree_hash=candidate.ui_tree_hash,
            screenshot_hash=candidate.screenshot_hash,
            stabilized=stabilized,
        )
        self.store.write_observation(
            session,
            observation,
            candidate.image,
            metadata=observation.model_dump(mode="json"),
            ui_tree_text=candidate.ui_tree_text,
        )
        return observation

    def _capture_observation_candidate(self, *, backend: AndroidRecordingBackend) -> "ObservationCandidate":
        image = backend.screenshot_bgr()
        current = backend.app_current()
        observation_tree = backend.capture_observation_tree()
        ui_tree_text = observation_tree.payload if observation_tree is not None else None
        ui_tree_hash = _hash_text(cast(str | None, ui_tree_text)) if ui_tree_text is not None else None
        screenshot_hash = _hash_bytes(image.tobytes())
        observation_hash = f"{current.entry_identity}|{current.surface_identity}|{ui_tree_hash or screenshot_hash}"
        current_app_state = RecordedCurrentAppState(
            platform=current.platform,
            entry_identity=current.entry_identity,
            surface_identity=current.surface_identity,
            url=current.url,
            title=current.title,
            load_state=current.load_state,
            raw=_trim_current_app_state_raw(cast(dict[str, object], current.raw)),
        )
        return ObservationCandidate(
            image=image,
            entry_identity=current.entry_identity,
            surface_identity=current.surface_identity,
            current_app_state=current_app_state,
            ui_tree_text=ui_tree_text,
            ui_tree_hash=ui_tree_hash,
            screenshot_hash=screenshot_hash,
            observation_hash=observation_hash,
        )


@dataclass
class ObservationCandidate:
    image: object
    entry_identity: str | None
    surface_identity: str | None
    current_app_state: RecordedCurrentAppState | None
    ui_tree_text: str | None
    ui_tree_hash: str | None
    screenshot_hash: str
    observation_hash: str


def _hash_text(value: str | None) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _trim_current_app_state_raw(raw: dict[str, object]) -> dict[str, object]:
    allowed_keys = {"url", "title", "load_state", "origin", "surface_identity"}
    return {key: value for key, value in raw.items() if key in allowed_keys and value is not None}
