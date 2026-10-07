from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from munk.agent_base.base import Brain, ScreenState
from munk.agent_base.types import Action
from munk.perception.types import ClickableElement


@dataclass
class ScreenFrame:
    signature: str
    targets: list[tuple[int, int, int, int]]


class SimpleTraversalBrain(Brain):
    def __init__(self) -> None:
        self._seen: set[str] = set()
        self._stack: list[ScreenFrame] = []
        self._awaiting_return = False

    def next_action(self, screen: ScreenState) -> Action:
        signature = self._signature(screen.elements)
        if self._awaiting_return:
            if self._stack and signature == self._stack[-1].signature:
                self._awaiting_return = False
            else:
                return Action.wait(0.5)
        frame = self._current_frame(signature)
        if frame is None and signature not in self._seen:
            frame = ScreenFrame(signature=signature, targets=self._targets(screen.elements))
            self._stack.append(frame)
            self._seen.add(signature)
        if frame and frame.targets:
            target = frame.targets.pop(0)
            return Action.click(target)
        if frame and self._stack and self._stack[-1].signature == signature:
            self._stack.pop()
        if self._stack:
            self._awaiting_return = True
            return Action.back()
        return Action.stop()

    def _current_frame(self, signature: str) -> ScreenFrame | None:
        if self._stack and self._stack[-1].signature == signature:
            return self._stack[-1]
        return None

    @staticmethod
    def _targets(elements: Iterable[ClickableElement]) -> list[tuple[int, int, int, int]]:
        return [element.box for element in elements]

    @staticmethod
    def _signature(elements: Iterable[ClickableElement]) -> str:
        items = sorted((e.kind, e.text, *e.box) for e in elements)
        return "|".join([",".join(map(str, item)) for item in items])
