from __future__ import annotations

import re

_STOPWORDS = {
    "the",
    "and",
    "with",
    "page",
    "screen",
    "task",
    "option",
    "button",
    "entry",
    "find",
    "look",
    "search",
    "click",
    "open",
    "back",
}


def extract_focus_terms(*texts: str) -> list[str]:
    keywords: set[str] = set()
    for text in texts:
        lowered = text.lower()
        quoted = re.findall(r"'([^']+)'|\"([^\"]+)\"", lowered)
        for pair in quoted:
            for item in pair:
                cleaned = item.strip()
                if cleaned:
                    keywords.add(cleaned)
        for token in re.findall(r"[a-zA-Z]{4,}|[\u4e00-\u9fff]{2,}", lowered):
            if token in _STOPWORDS:
                continue
            keywords.add(token)
        phrase_tokens = re.findall(r"[a-zA-Z]{2,}|[\u4e00-\u9fff]{2,}", lowered)
        for size in (2, 3):
            for index in range(len(phrase_tokens) - size + 1):
                phrase = " ".join(phrase_tokens[index : index + size]).strip()
                if not phrase:
                    continue
                keywords.add(phrase)
    return sorted(keywords)


def count_focus_matches(text: str, focus_terms: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in focus_terms if term and term in lowered)
