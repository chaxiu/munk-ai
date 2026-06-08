from __future__ import annotations

import json
import time
from typing import Any, cast
from urllib.parse import urlparse

import cv2
import numpy as np
from munk.app import AppTarget
from munk.device import CurrentAppState, RuntimeLogEntry, RuntimeLogLevel
from munk.perception import ObservationTree
from munk.perception.image import BgrImage
from playwright.sync_api import sync_playwright  # pyright: ignore[reportMissingImports]


class WebDevice:
    def __init__(self, *, device_ref: str | None = None, app_target: AppTarget) -> None:
        if app_target.platform != "web" or app_target.web is None:
            raise ValueError("web runtime requires a web app_target")
        self._device_ref = device_ref
        self._app_target = app_target
        self._playwright_manager: Any | None = None
        self._playwright: Any | None = None
        self._browser: Any | None = None
        self._context: Any | None = None
        self._page: Any | None = None
        self._runtime_logs: list[RuntimeLogEntry] = []
        self._log_session_started = False

    @property
    def device_calls_thread_safe(self) -> bool:
        return False

    def screenshot_bgr(self) -> BgrImage:
        page = self._ensure_page()
        payload = page.screenshot(type="png")
        if not isinstance(payload, bytes):
            raise ValueError("web screenshot not returned as bytes")
        return _decode_png_to_bgr(payload)

    def click(self, x: int, y: int) -> None:
        page = self._ensure_page()
        page.mouse.click(x, y)

    def long_press(self, x: int, y: int, duration: float | None = None) -> None:
        page = self._ensure_page()
        hold_duration = duration if duration is not None else 1.0
        page.mouse.move(x, y)
        page.mouse.down()
        time.sleep(max(hold_duration, 0.0))
        page.mouse.up()

    def scroll(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        duration: float | None = None,
    ) -> None:
        del duration
        page = self._ensure_page()
        page.mouse.move(start[0], start[1])
        page.mouse.wheel(start[0] - end[0], start[1] - end[1])

    def press(self, key: str) -> None:
        page = self._ensure_page()
        normalized = key.strip().lower()
        if normalized == "back":
            page.go_back(wait_until="domcontentloaded")
            return
        if normalized == "home":
            page.goto(self._resolve_launch_url(self._app_target.entry_identity), wait_until="domcontentloaded")
            return
        page.keyboard.press(key)

    def input_text(self, text: str) -> None:
        page = self._ensure_page()
        page.keyboard.type(text)

    def clear_text(self) -> None:
        page = self._ensure_page()
        cleared = page.evaluate(_CLEAR_ACTIVE_TEXT_SCRIPT)
        if cleared is True:
            return
        page.keyboard.press("Meta+A")
        page.keyboard.press("Backspace")

    def app_start(self, entry_identity: str) -> None:
        self._ensure_browser()
        self._close_context()
        browser = self._browser
        if browser is None:
            raise RuntimeError("browser not initialized")
        context = browser.new_context(viewport=self._viewport_size())
        page = context.new_page()
        self._bind_console_listener(page)
        page.goto(self._resolve_launch_url(entry_identity), wait_until="domcontentloaded")
        self._context = context
        self._page = page

    def app_stop(self, entry_identity: str) -> None:
        del entry_identity
        self._close_context()

    def app_current(self) -> CurrentAppState:
        page = self._ensure_page()
        current_url = getattr(page, "url", None)
        url = current_url if isinstance(current_url, str) and current_url else None
        title = page.title()
        normalized_title = title if isinstance(title, str) and title else None
        load_state = _read_page_load_state(page)
        entry_identity = _origin_from_url(url) or self._app_target.entry_identity
        surface_identity = _surface_identity_from_url(url) or entry_identity
        raw = {
            "url": url,
            "title": normalized_title,
            "load_state": load_state,
            "origin": entry_identity,
            "surface_identity": surface_identity,
        }
        return CurrentAppState(
            platform="web",
            entry_identity=entry_identity,
            surface_identity=surface_identity,
            url=url,
            title=normalized_title,
            load_state=load_state,
            raw={key: value for key, value in raw.items() if value is not None},
        )

    def window_size(self) -> tuple[int, int]:
        page = self._ensure_page()
        viewport_size = getattr(page, "viewport_size", None)
        if isinstance(viewport_size, dict):
            width = _to_int(viewport_size.get("width"), self._viewport_size()["width"])
            height = _to_int(viewport_size.get("height"), self._viewport_size()["height"])
            return width, height
        payload = page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight })")
        if isinstance(payload, dict):
            return (
                _to_int(payload.get("width"), self._viewport_size()["width"]),
                _to_int(payload.get("height"), self._viewport_size()["height"]),
            )
        size = self._viewport_size()
        return size["width"], size["height"]

    def capture_observation_tree(self) -> ObservationTree | None:
        page = self._ensure_page()
        payload = page.evaluate(_DOM_SNAPSHOT_SCRIPT)
        if not isinstance(payload, dict):
            return None
        payload_dict = cast(dict[str, object], payload)
        nodes = payload_dict.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            return None
        return ObservationTree(
            source_type="web_dom",
            content_type="json",
            payload=json.dumps(payload_dict, ensure_ascii=False),
        )

    def start_log_session(self) -> None:
        self._log_session_started = True
        self._runtime_logs.clear()

    def drain_runtime_logs(self) -> list[RuntimeLogEntry]:
        entries = list(self._runtime_logs)
        self._runtime_logs.clear()
        return entries

    def stop_log_session(self) -> None:
        self._log_session_started = False
        self._runtime_logs.clear()

    def close(self) -> None:
        self._close_context()
        browser = self._browser
        if browser is not None:
            browser.close()
            self._browser = None
        playwright = self._playwright
        if playwright is not None:
            playwright.stop()
            self._playwright = None
        self._playwright_manager = None

    def _ensure_browser(self) -> None:
        if self._browser is not None:
            return
        manager = sync_playwright()
        playwright = manager.start()
        browser_type_name = self._app_target.launch_context.get("browser", "chromium").strip().lower() or "chromium"
        if browser_type_name != "chromium":
            playwright.stop()
            raise ValueError(f"web runtime only supports chromium in MP1, got: {browser_type_name}")
        browser_type = getattr(playwright, browser_type_name, None)
        if browser_type is None:
            playwright.stop()
            raise ValueError(f"playwright browser '{browser_type_name}' is not available")
        self._playwright_manager = manager
        self._playwright = playwright
        if self._device_ref:
            self._browser = browser_type.connect_over_cdp(self._device_ref)
            return
        self._browser = browser_type.launch(headless=_parse_bool(self._app_target.launch_context.get("headless"), False))

    def _ensure_page(self) -> Any:
        if self._page is not None:
            return self._page
        self.app_start(self._app_target.entry_identity or "")
        if self._page is None:
            raise RuntimeError("page not initialized")
        return self._page

    def _resolve_launch_url(self, entry_identity: str | None) -> str:
        web = self._app_target.web
        if web is None:
            raise ValueError("web runtime requires web identity details")
        url = web.base_url or entry_identity or self._app_target.entry_identity
        if not url:
            raise ValueError("web runtime requires app_target.web.base_url or entry_identity")
        return url

    def _viewport_size(self) -> dict[str, int]:
        return {
            "width": _to_int(self._app_target.launch_context.get("viewport_width"), 1440),
            "height": _to_int(self._app_target.launch_context.get("viewport_height"), 900),
        }

    def _close_context(self) -> None:
        context = self._context
        self._page = None
        self._context = None
        self._runtime_logs.clear()
        if context is not None:
            context.close()

    def _bind_console_listener(self, page: Any) -> None:
        on = getattr(page, "on", None)
        if not callable(on):
            return
        on("console", self._handle_console_message)

    def _handle_console_message(self, message: Any) -> None:
        if not self._log_session_started:
            return
        message_type = _read_console_message_type(message)
        text = _read_console_message_text(message)
        if not text:
            return
        page = self._page
        page_url = getattr(page, "url", None) if page is not None else None
        current_url = page_url if isinstance(page_url, str) and page_url else None
        location = _read_console_message_location(message)
        self._runtime_logs.append(
            RuntimeLogEntry(
                timestamp_ms=int(time.time() * 1000),
                level=cast(RuntimeLogLevel, _console_level(message_type)),
                source="web_console",
                message=text,
                raw={
                    "type": message_type,
                    "location": location,
                    "page_url": current_url,
                },
                target_identity=_origin_from_url(current_url) or self._app_target.entry_identity,
                surface_identity=_surface_identity_from_url(current_url) or current_url,
            )
        )


def _decode_png_to_bgr(payload: bytes) -> BgrImage:
    buffer = np.frombuffer(payload, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("failed to decode playwright screenshot")
    return cast(BgrImage, image)


def _origin_from_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _surface_identity_from_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url
    path = parsed.path or "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _read_page_load_state(page: Any) -> str | None:
    payload = page.evaluate("() => document.readyState")
    if not isinstance(payload, str):
        return None
    normalized = payload.strip().lower()
    if normalized in {"loading", "interactive", "complete"}:
        return normalized
    return None


def _to_int(value: object, fallback: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return fallback
    return fallback


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _read_console_message_type(message: Any) -> str:
    value = getattr(message, "type", None)
    if callable(value):
        value = value()
    if isinstance(value, str) and value.strip():
        return value.strip().lower()
    return "unknown"


def _read_console_message_text(message: Any) -> str:
    value = getattr(message, "text", None)
    if callable(value):
        value = value()
    if isinstance(value, str):
        return value.strip()
    return ""


def _read_console_message_location(message: Any) -> dict[str, object]:
    value = getattr(message, "location", None)
    if callable(value):
        value = value()
    if isinstance(value, dict):
        return dict(value)
    return {}


def _console_level(message_type: str) -> str:
    if message_type in {"error", "assert"}:
        return "error"
    if message_type in {"warning", "warn"}:
        return "warning"
    if message_type in {"debug", "trace"}:
        return "debug"
    if message_type in {"info", "log"}:
        return "info"
    return "unknown"


_DOM_SNAPSHOT_SCRIPT = """
() => {
  const isVisible = (element) => {
    const style = window.getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity || "1") === 0) {
      return false;
    }
    const rect = element.getBoundingClientRect();
    return rect.width > 1 && rect.height > 1;
  };
  const isClickable = (element, role) => {
    const tag = element.tagName.toLowerCase();
    if (typeof element.onclick === "function") {
      return true;
    }
    if (element.hasAttribute("href")) {
      return true;
    }
    if (element.tabIndex >= 0 && role !== "textbox") {
      return true;
    }
    return ["a", "button", "summary"].includes(tag) || role === "button" || role === "link";
  };
  const isCheckable = (element, role) => {
    const inputType = (element.getAttribute("type") || "").toLowerCase();
    return ["checkbox", "radio"].includes(inputType) || role === "checkbox" || role === "switch";
  };
  const nodes = [];
  let counter = 0;
  for (const element of document.querySelectorAll("body *")) {
    if (!(element instanceof HTMLElement)) {
      continue;
    }
    if (!isVisible(element)) {
      continue;
    }
    const rect = element.getBoundingClientRect();
    const role = (element.getAttribute("role") || "").trim().toLowerCase() || null;
    const text = (element.innerText || element.textContent || "").replace(/\\s+/g, " ").trim() || null;
    const name = (
      element.getAttribute("aria-label") ||
      element.getAttribute("title") ||
      element.getAttribute("placeholder") ||
      element.getAttribute("name") ||
      ""
    ).replace(/\\s+/g, " ").trim() || null;
    const tagName = element.tagName.toLowerCase();
    const scrollable = element.scrollHeight > element.clientHeight + 1 || element.scrollWidth > element.clientWidth + 1;
    const node = {
      node_id: `node-${counter++}`,
      bounds: [
        Math.round(rect.left),
        Math.round(rect.top),
        Math.round(rect.right),
        Math.round(rect.bottom),
      ],
      tag_name: tagName,
      role,
      text,
      name,
      resource_id: element.id || null,
      clickable: isClickable(element, role),
      checkable: isCheckable(element, role),
      checked: element.getAttribute("aria-checked") === "true" || ("checked" in element && Boolean(element.checked)),
      enabled: !element.hasAttribute("disabled") && element.getAttribute("aria-disabled") !== "true",
      focused: document.activeElement === element,
      selected: element.getAttribute("aria-selected") === "true",
      scrollable,
    };
    if (
      !node.clickable &&
      !node.checkable &&
      !node.scrollable &&
      !node.text &&
      !node.name &&
      !node.resource_id &&
      !node.role
    ) {
      continue;
    }
    nodes.push(node);
  }
  return {
    format_version: 1,
    url: window.location.href,
    title: document.title || null,
    nodes,
  };
}
"""


_CLEAR_ACTIVE_TEXT_SCRIPT = """
() => {
  const element = document.activeElement;
  if (!element) {
    return false;
  }
  if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) {
    element.value = "";
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }
  if (element instanceof HTMLElement && element.isContentEditable) {
    element.textContent = "";
    element.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  }
  return false;
}
"""
