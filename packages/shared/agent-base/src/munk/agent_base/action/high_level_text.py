from __future__ import annotations

import time

from munk.core.observation import observe_action_result

from ..base import ScreenState
from ..types import Action
from .executor import ActionExecutor, ActionExecutionError
from .high_level_common import (
    HighLevelActionResult,
    ObservationRefresher,
    SCROLL_UNTIL_TEXT_NOT_FOUND_ERROR,
    SCROLL_UNTIL_TEXT_STAGNATED_ERROR,
    TEXT_RECENTER_START_Y_RATIO,
    from_atomic_result,
)
from .high_level_screen import (
    build_text_match_summary,
    locate_matched_text_box,
    resolve_text_recenter_adjustment,
    screen_matches_text_condition,
)


class HighLevelTextHandler:
    def __init__(self, executor: ActionExecutor) -> None:
        self._executor = executor

    def execute_wait_for_text(
        self,
        action: Action,
        screen: ScreenState,
        capture_observation: ObservationRefresher,
    ) -> HighLevelActionResult:
        match_type, match_texts = self._validate_text_match_spec(action)
        deadline = time.monotonic() + (action.duration or 0.0)
        current = screen
        while True:
            if screen_matches_text_condition(current, match_type=match_type, texts=match_texts):
                return HighLevelActionResult(
                    executed=True,
                    timed_out=False,
                    action=action,
                    normalized_action=action,
                    duration_ms=0,
                    postcheck_passed=True,
                    postcheck_summary=build_text_match_summary(
                        match_type=match_type,
                        texts=match_texts,
                    ),
                )
            if time.monotonic() >= deadline:
                raise ActionExecutionError(
                    "wait_for_text timed out: "
                    + build_text_match_summary(match_type=match_type, texts=match_texts)
                )
            time.sleep(0.2)
            current = capture_observation("post_action_retry").screen

    def execute_scroll_until_text(
        self,
        action: Action,
        screen: ScreenState,
        capture_observation: ObservationRefresher,
    ) -> HighLevelActionResult:
        match_type, match_texts = self._validate_text_match_spec(action)
        current = screen
        attempts = action.max_attempts or 1
        stagnant_rounds = 0
        for _ in range(attempts):
            if screen_matches_text_condition(current, match_type=match_type, texts=match_texts):
                centered_or_result = self._maybe_recenter_matched_text(
                    action,
                    current,
                    capture_observation,
                    match_type=match_type,
                    texts=match_texts,
                )
                if isinstance(centered_or_result, HighLevelActionResult):
                    return centered_or_result
                return HighLevelActionResult(
                    executed=True,
                    timed_out=False,
                    action=action,
                    normalized_action=action,
                    duration_ms=0,
                    postcheck_passed=True,
                    postcheck_summary=build_text_match_summary(
                        match_type=match_type,
                        texts=match_texts,
                    ),
                )
            execution = self._executor.execute(
                self._build_scroll_action(action.direction or "down")
            )
            if not execution.executed:
                return from_atomic_result(action, execution)
            next_screen = capture_observation("post_action_retry").screen
            observation = observe_action_result(current, next_screen)
            if not observation.screen_changed:
                stagnant_rounds += 1
                if stagnant_rounds >= 2:
                    return HighLevelActionResult(
                        executed=False,
                        timed_out=False,
                        action=action,
                        normalized_action=action,
                        duration_ms=0,
                        error_type="ActionExecutionError",
                        error_message=SCROLL_UNTIL_TEXT_STAGNATED_ERROR,
                    )
            else:
                stagnant_rounds = 0
            current = next_screen
        return HighLevelActionResult(
            executed=False,
            timed_out=False,
            action=action,
            normalized_action=action,
            duration_ms=0,
            error_type="ActionExecutionError",
            error_message=SCROLL_UNTIL_TEXT_NOT_FOUND_ERROR,
        )

    def _maybe_recenter_matched_text(
        self,
        action: Action,
        screen: ScreenState,
        capture_observation: ObservationRefresher,
        *,
        match_type: str,
        texts: tuple[str, ...],
    ) -> ScreenState | HighLevelActionResult:
        if match_type == "none_of_texts":
            return screen
        matched_box = locate_matched_text_box(
            screen,
            match_type=match_type,
            texts=texts,
        )
        if matched_box is None:
            return screen
        scroll_direction, distance_ratio = resolve_text_recenter_adjustment(
            matched_box,
            screen_size=screen.screen_size,
        )
        if scroll_direction is None or distance_ratio <= 0:
            return screen
        execution = self._executor.execute(
            self._build_scroll_action(
                scroll_direction,
                start_y_ratio=TEXT_RECENTER_START_Y_RATIO,
                distance_ratio=distance_ratio,
                summary=f"recenter matched text {scroll_direction}",
            )
        )
        if not execution.executed:
            return from_atomic_result(action, execution)
        next_screen = capture_observation("post_action_retry").screen
        observation = observe_action_result(screen, next_screen)
        if not observation.screen_changed:
            raise ActionExecutionError("target_matched_but_not_centered_after_scroll")
        if not screen_matches_text_condition(next_screen, match_type=match_type, texts=texts):
            raise ActionExecutionError("target_lost_after_centering_scroll")
        return next_screen

    @staticmethod
    def _validate_text_match_spec(action: Action) -> tuple[str, tuple[str, ...]]:
        match_type = (action.match_type or "").strip()
        if match_type not in {"any_of_texts", "all_texts", "none_of_texts"}:
            raise ActionExecutionError(f"{action.type.value} requires a valid match_type")
        texts = tuple(text for text in (action.match_texts or ()) if text.strip())
        if not texts:
            raise ActionExecutionError(f"{action.type.value} requires non-empty match_texts")
        return match_type, texts

    @staticmethod
    def _build_scroll_action(
        direction: str,
        *,
        start_x_ratio: float = 0.5,
        start_y_ratio: float = 0.75,
        distance_ratio: float = 0.5,
        summary: str | None = None,
    ) -> Action:
        if direction.lower() == "up":
            return Action.scroll(
                direction="up",
                start_x_ratio=start_x_ratio,
                start_y_ratio=start_y_ratio,
                distance_ratio=distance_ratio,
                summary=summary or "scroll up",
            )
        return Action.scroll(
            direction="down",
            start_x_ratio=start_x_ratio,
            start_y_ratio=start_y_ratio,
            distance_ratio=distance_ratio,
            summary=summary or "scroll down",
        )
