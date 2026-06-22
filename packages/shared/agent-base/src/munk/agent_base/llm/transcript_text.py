from __future__ import annotations

import json
from typing import Mapping

from pydantic import BaseModel

from .transcript_models import LlmTranscriptEntry, parse_llm_transcript_entry


def extract_transcript_entry_text(entry: LlmTranscriptEntry | Mapping[str, object]) -> str | None:
    normalized = entry if isinstance(entry, BaseModel) else parse_llm_transcript_entry(entry)
    if normalized is None:
        return None
    if normalized.kind == "llm_request":
        return clean_text(extract_request_text(normalized.body))
    if normalized.kind == "llm_response":
        return clean_text(extract_response_text(normalized.body))
    return None


def extract_request_text(body: object) -> str | None:
    if isinstance(body, Mapping):
        messages = body.get("messages")
        if isinstance(messages, list):
            rendered_messages = [render_chat_message(message) for message in messages]
            message_text = "\n\n".join(item for item in rendered_messages if item)
            if message_text:
                return message_text
        input_value = body.get("input")
        if input_value is not None:
            input_text = extract_text_content(input_value)
            if input_text:
                return input_text
    return fallback_json_text(body)


def extract_response_text(body: object) -> str | None:
    if isinstance(body, Mapping):
        sections = extract_response_sections(body)
        if sections:
            return "\n\n".join(f"{title}\n{text}" for title, text in sections if text)
    return fallback_json_text(body)


def extract_response_sections(body: Mapping[str, object]) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    choices = body.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            if not isinstance(choice, Mapping):
                continue
            message = choice.get("message")
            if not isinstance(message, Mapping):
                continue
            reasoning_text = extract_text_content(message.get("reasoning")) or extract_text_content(
                message.get("reasoning_content")
            )
            response_text = extract_text_content(message.get("content"))
            if reasoning_text:
                sections.append(("Reasoning", reasoning_text))
            if response_text:
                sections.append(("Response", response_text))
            if sections:
                return sections
    output = body.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, Mapping):
                continue
            item_type = str(item.get("type") or "")
            if item_type == "reasoning":
                reasoning_text = extract_text_content(item.get("summary")) or extract_text_content(item.get("content"))
                if reasoning_text:
                    sections.append(("Reasoning", reasoning_text))
                continue
            if item_type in {"message", "output_text"}:
                response_text = extract_text_content(item.get("content")) or extract_text_content(item.get("text"))
                if response_text:
                    sections.append(("Response", response_text))
        if sections:
            return sections
    reasoning_text = extract_text_content(body.get("reasoning")) or extract_text_content(body.get("reasoning_content"))
    response_text = extract_text_content(body.get("output_text")) or extract_text_content(body.get("content"))
    if reasoning_text:
        sections.append(("Reasoning", reasoning_text))
    if response_text:
        sections.append(("Response", response_text))
    return sections


def render_chat_message(message: object) -> str | None:
    if not isinstance(message, Mapping):
        return None
    role = str(message.get("role") or "message").upper()
    parts: list[str] = []
    reasoning_text = extract_text_content(message.get("reasoning")) or extract_text_content(message.get("reasoning_content"))
    if reasoning_text:
        parts.append(f"[reasoning]\n{reasoning_text}")
    content_text = extract_text_content(message.get("content"))
    if content_text:
        parts.append(content_text)
    if not parts:
        return None
    return f"{role}\n" + "\n\n".join(parts)


def extract_text_content(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, list):
        parts = [extract_text_content(item) for item in value]
        combined = "\n".join(item for item in parts if item)
        return clean_text(combined)
    if not isinstance(value, Mapping):
        return None
    block_type = str(value.get("type") or "")
    if block_type in {"text", "input_text", "output_text"}:
        return clean_text(value.get("text"))
    if block_type in {"image", "image_url", "input_image"}:
        return describe_image_block(value)
    if "text" in value:
        text_value = clean_text(value.get("text"))
        if text_value:
            return text_value
    if "content" in value:
        content_text = extract_text_content(value.get("content"))
        if content_text:
            return content_text
    if "summary" in value:
        summary_text = extract_text_content(value.get("summary"))
        if summary_text:
            return summary_text
    if "image_url" in value:
        return describe_image_block(value)
    return None


def describe_image_block(value: Mapping[str, object]) -> str:
    image_url = value.get("image_url")
    if isinstance(image_url, Mapping):
        media_type = image_url.get("media_type")
        url = image_url.get("url")
        if isinstance(url, str) and url and url != "<omitted:data-image>":
            return f"[image] {url}"
        if isinstance(media_type, str) and media_type:
            return f"[image] {media_type}"
    return "[image]"


def fallback_json_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return clean_text(value)
    try:
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    except TypeError:
        return clean_text(str(value))


def clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.replace("\r\n", "\n").strip()
    return cleaned or None
