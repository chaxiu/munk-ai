from munk.agent_runtime import AgentRuntimeEvent, AgentRuntimeEventEmitter


def test_agent_runtime_event_fields_are_stable() -> None:
    event = AgentRuntimeEvent(
        event_type="review_retrieval_completed",
        lifecycle_state="running",
        timestamp="2026-01-01T00:00:00+00:00",
        agent_role="review",
        operation_id="op-1",
        message="review retrieval completed",
        data={"hit_count": 1},
    )

    assert event.event_type == "review_retrieval_completed"
    assert event.lifecycle_state == "running"
    assert event.agent_role == "review"
    assert event.data == {"hit_count": 1}


def test_agent_runtime_event_emitter_emits_standard_lifecycle_events() -> None:
    events: list[AgentRuntimeEvent] = []

    class CollectingSink:
        def emit(self, event: AgentRuntimeEvent) -> None:
            events.append(event)

    emitter = AgentRuntimeEventEmitter(
        agent_role="review",
        operation_id="op-1",
        event_sink=CollectingSink(),
    )

    emitter.emit_started(message="started")
    emitter.emit_progress(event_type="review_context_loaded", message="context loaded")
    emitter.emit_failed(message="failed")

    assert [event.event_type for event in events] == [
        "agent_started",
        "review_context_loaded",
        "agent_failed",
    ]
    assert [event.lifecycle_state for event in events] == [
        "started",
        "running",
        "failed",
    ]
    assert all(event.agent_role == "review" for event in events)
    assert all(event.operation_id == "op-1" for event in events)


def test_cancel_controller_contract_can_be_implemented_directly() -> None:
    class AlwaysCancelledController:
        def is_cancel_requested(self) -> bool:
            return True

    controller = AlwaysCancelledController()
    assert controller.is_cancel_requested() is True
