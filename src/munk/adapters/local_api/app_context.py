from __future__ import annotations

from pathlib import Path

from munk.adapters.local_api.background_operations import LocalBackgroundOperationSupervisor
from munk.scheduling.executor_service import ScheduleExecutorService
from munk.scheduling.registry import ScheduleRegistry
from munk.scheduling.runner import ScheduleRunner
from munk.services.interactive import InteractiveService
from munk.services.machine_command_service import MachineCommandService
from munk.services.operations.registry import OperationRegistry
from munk.services.recording.session_service import RecordingSessionService
from munk.user_data import ensure_home_layout


class LocalApiAppContext:
    def __init__(
        self,
        *,
        project_root: Path,
        workspace_root: Path,
        start_recording_bridge: bool,
        recording_service: RecordingSessionService | None = None,
    ) -> None:
        self.project_root = project_root
        self.workspace_root = workspace_root
        self.start_recording_bridge = start_recording_bridge
        self.background_operation_supervisor = LocalBackgroundOperationSupervisor()
        self._machine_service: MachineCommandService | None = None
        self._recording_service = recording_service
        self._interactive_service: InteractiveService | None = None
        self._schedule_runner: ScheduleRunner | None = None

    def get_machine_service(self) -> MachineCommandService:
        if self._machine_service is None:
            ensure_home_layout()
            self._machine_service = MachineCommandService(workspace_root=self.workspace_root)
        return self._machine_service

    def get_recording_service(self) -> RecordingSessionService:
        if self._recording_service is None:
            self._recording_service = RecordingSessionService(
                project_root=self.project_root,
                workspace_root=self.workspace_root,
            )
        return self._recording_service

    def get_interactive_service(self) -> InteractiveService:
        if self._interactive_service is None:
            self._interactive_service = InteractiveService()
        return self._interactive_service

    def get_schedule_runner(self) -> ScheduleRunner:
        if self._schedule_runner is None:
            self._schedule_runner = ScheduleRunner(
                executor=ScheduleExecutorService(
                    registry=ScheduleRegistry(),
                    machine_service=self.get_machine_service(),
                    operation_registry=OperationRegistry(),
                    background_submitter=self.background_operation_supervisor.submit,
                )
            )
        return self._schedule_runner

    def request_background_cancel(self, operation_id: str) -> None:
        self.get_machine_service().cancel_operation(operation_id=operation_id)

    @property
    def schedule_runner(self) -> ScheduleRunner | None:
        return self._schedule_runner

    @property
    def recording_service(self) -> RecordingSessionService | None:
        return self._recording_service
