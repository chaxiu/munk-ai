from __future__ import annotations

import re
from typing import Iterable

from munk.perception.types import ClickableElement, IconDetection, TextDetection

from .geometry import box_iou

_WORD_PATTERN = re.compile(r"[A-Za-z0-9]+")
_CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uF900-\uFAFF]")


def _normalize_text_whitespace(text: str) -> str:
    return " ".join(text.split())


def _text_units(text: str) -> int:
    if not text:
        return 0
    word_count = len(_WORD_PATTERN.findall(text))
    cjk_count = len(_CJK_PATTERN.findall(text))
    return word_count + cjk_count


def fuse_elements(
    icons: Iterable[IconDetection],
    texts: Iterable[TextDetection],
    min_text_length: int = 1,
    icon_text_max_length: int = 8,
    max_text_length: int = 8,
    match_iou: float = 0.3,
) -> list[ClickableElement]:
    icon_list = list(icons)
    text_list = list(texts)
    icon_texts: list[str] = ["" for _ in icon_list]
    for text in text_list:
        cleaned = _normalize_text_whitespace(text.text)
        units = _text_units(text.text)
        if units < min_text_length or units > icon_text_max_length:
            continue
        best_idx = -1
        best_iou = 0.0
        for idx, icon in enumerate(icon_list):
            iou = box_iou(text.box, icon.box)
            if iou > best_iou:
                best_iou = iou
                best_idx = idx
        if best_idx >= 0 and best_iou >= match_iou:
            if icon_texts[best_idx]:
                icon_texts[best_idx] = f"{icon_texts[best_idx]} {cleaned}"
            else:
                icon_texts[best_idx] = cleaned
    elements: list[ClickableElement] = []
    for icon, text in zip(icon_list, icon_texts):
        elements.append(ClickableElement(icon.box, "icon", text, icon.score))
    for text in text_list:
        cleaned = _normalize_text_whitespace(text.text)
        units = _text_units(text.text)
        if units < min_text_length or units > max_text_length:
            continue
        elements.append(ClickableElement(text.box, "text", cleaned, text.score))
    return elements
