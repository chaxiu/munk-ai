from __future__ import annotations

import json
import time
from threading import get_ident
from types import SimpleNamespace
from typing import Callable, cast

import cv2
import numpy as np
from munk.app import AppTarget, WebAppIdentity
from munk.device import (
    CurrentAppState,
    DeviceDriver,
    SupportsAppLifecycle,
    SupportsClose,
    SupportsElementTargetAction,
    SupportsRuntimeLogs,
    SupportsTextClear,
)
from munk_device_web import WebDevice


class FakeMouse:
    def __init__(self) -> None:
        self.click_calls: list[tuple[int, int]] = []
        self.move_calls: list[tuple[int, int, int | None]] = []
        self.wheel_calls: list[tuple[int, int]] = []
        self.down_calls = 0
        self.up_calls = 0

    def click(self, x: int, y: int) -> None:
        self.click_calls.append((x, y))

    def move(self, x: int, y: int, *, steps: int | None = None) -> None:
        self.move_calls.append((x, y, steps))

    def wheel(self, delta_x: int, delta_y: int) -> None:
        self.wheel_calls.append((delta_x, delta_y))

    def down(self) -> None:
        self.down_calls += 1

    def up(self) -> None:
        self.up_calls += 1


class FakeKeyboard:
    def __init__(self) -> None:
        self.type_calls: list[str] = []
        self.press_calls: list[str] = []

    def type(self, text: str) -> None:
        self.type_calls.append(text)

    def press(self, key: str) -> None:
        self.press_calls.append(key)


class FakeLocator:
    def __init__(self, page: "FakePage") -> None:
        self.page = page
        self.fill_calls: list[str] = []
        self.click_calls = 0
        self.select_calls: list[str] = []
        self.check_calls = 0
        self.uncheck_calls = 0
        self.dispatch_calls: list[str] = []
        self._value = ""
        self._checked = False

    @property
    def first(self) -> "FakeLocator":
        return self

    def click(self) -> None:
        self.click_calls += 1

    def fill(self, text: str) -> None:
        self.fill_calls.append(text)
        self._value = text

    def select_option(self, text: str) -> None:
        self.select_calls.append(text)
        self._value = text

    def check(self) -> None:
        self.check_calls += 1
        self._checked = True

    def uncheck(self) -> None:
        self.uncheck_calls += 1
        self._checked = False

    def dispatch_event(self, name: str) -> None:
        self.dispatch_calls.append(name)

    def press(self, key: str) -> None:
        self.page.keyboard.press(key)

    def input_value(self) -> str:
        return self._value

    def is_checked(self) -> bool:
        return self._checked

    def evaluate(self, script: str) -> object:
        del script
        return self._value


class FakePage:
    def __init__(self) -> None:
        self.mouse = FakeMouse()
        self.keyboard = FakeKeyboard()
        self.url = "https://example.com/dashboard"
        self._title = "Dashboard"
        self._ready_state = "complete"
        self._dom_snapshot: dict[str, object] = {
            "format_version": 1,
            "url": "https://example.com/dashboard",
            "title": "Dashboard",
            "nodes": [
                {
                    "node_id": "node-0",
                    "bounds": [10, 20, 110, 70],
                    "tag_name": "button",
                    "role": "button",
                    "text": "hello",
                    "name": "hello",
                    "attr_name": None,
                    "resource_id": "confirm",
                    "input_type": None,
                    "value": None,
                    "test_id": None,
                    "clickable": True,
                    "checkable": False,
                    "checked": False,
                    "enabled": True,
                    "focused": False,
                    "selected": False,
                    "scrollable": False,
                },
                {
                    "node_id": "node-1",
                    "bounds": [10, 80, 210, 120],
                    "tag_name": "input",
                    "role": None,
                    "text": None,
                    "name": "Due date",
                    "attr_name": "dueDate",
                    "resource_id": None,
                    "input_type": "date",
                    "value": "",
                    "test_id": "due-date",
                    "clickable": True,
                    "checkable": False,
                    "checked": False,
                    "enabled": True,
                    "focused": False,
                    "selected": False,
                    "scrollable": False,
                },
            ],
        }
        self.viewport_size = {"width": 1280, "height": 720}
        self.goto_calls: list[tuple[str, str]] = []
        self.go_back_calls: list[str] = []
        self.listeners: dict[str, list[Callable[[object], None]]] = {}
        self.active_text = "prefilled value"
        self.last_locator: FakeLocator | None = None
        self.locator_calls: list[str] = []
        self.screenshot_thread_ids: list[int] = []
        self.goto_thread_ids: list[int] = []

    def locator(self, selector: str) -> FakeLocator:
        self.locator_calls.append(selector)
        self.last_locator = FakeLocator(self)
        return self.last_locator

    def screenshot(self, *, type: str) -> bytes:  # noqa: A002
        assert type == "png"
        self.screenshot_thread_ids.append(get_ident())
        image = np.zeros((2, 3, 3), dtype=np.uint8)
        image[:, :] = (1, 2, 3)
        ok, payload = cv2.imencode(".png", image)
        assert ok is True
        return payload.tobytes()

    def title(self) -> str:
        return self._title

    def goto(self, url: str, *, wait_until: str) -> None:
        self.goto_thread_ids.append(get_ident())
        self.goto_calls.append((url, wait_until))
        self.url = url

    def go_back(self, *, wait_until: str) -> None:
        self.go_back_calls.append(wait_until)

    def evaluate(self, script: str) -> object:
        if "format_version" in script:
            return self._dom_snapshot
        if "document.readyState" in script:
            return self._ready_state
        if 'element.value = ""' in script:
            self.active_text = ""
            return True
        return {"width": 1280, "height": 720}

    def on(self, event: str, callback: Callable[[object], None]) -> None:
        self.listeners.setdefault(event, []).append(callback)

    def emit_console(
        self,
        *,
        message_type: str,
        text: str,
        location_url: str = "https://example.com/app.js",
    ) -> None:
        callbacks = self.listeners.get("console", [])
        message = SimpleNamespace(
            type=message_type,
            text=text,
            location={"url": location_url},
        )
        for callback in callbacks:
            callback(message)


class FakeContext:
    def __init__(self, page: FakePage) -> None:
        self.page = page
        self.closed = False

    def new_page(self) -> FakePage:
        return self.page

    def close(self) -> None:
        self.closed = True
        self.page.listeners.clear()


class FakeBrowser:
    def __init__(self, page: FakePage) -> None:
        self.page = page
        self.contexts: list[FakeContext] = []
        self.closed = False
        self.close_thread_ids: list[int] = []

    def new_context(self, *, viewport: dict[str, int]) -> FakeContext:
        del viewport
        context = FakeContext(self.page)
        self.contexts.append(context)
        return context

    def close(self) -> None:
        self.close_thread_ids.append(get_ident())
        self.closed = True


class FakeBrowserType:
    def __init__(self, browser: FakeBrowser) -> None:
        self.browser = browser
        self.launch_calls: list[bool] = []
        self.cdp_calls: list[str] = []
        self.launch_thread_ids: list[int] = []

    def launch(self, *, headless: bool) -> FakeBrowser:
        self.launch_thread_ids.append(get_ident())
        self.launch_calls.append(headless)
        return self.browser

    def connect_over_cdp(self, endpoint: str) -> FakeBrowser:
        self.cdp_calls.append(endpoint)
        return self.browser


class FakePlaywright:
    def __init__(self, browser_type: FakeBrowserType) -> None:
        self.chromium = browser_type
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


class FakePlaywrightManager:
    def __init__(self, playwright: FakePlaywright) -> None:
        self.playwright = playwright

    def start(self) -> FakePlaywright:
        return self.playwright


def build_app_target(**launch_context: str) -> AppTarget:
    return AppTarget(
        app_id="web-app",
        platform="web",
        web=WebAppIdentity(base_url="https://example.com/app", origin="https://example.com"),
        launch_context=launch_context,
    )


def build_device(monkeypatch, *, device_ref: str | None = None, **launch_context: str) -> tuple[WebDevice, FakePage, FakeBrowserType]:
    page = FakePage()
    browser = FakeBrowser(page)
    browser_type = FakeBrowserType(browser)
    manager = FakePlaywrightManager(FakePlaywright(browser_type))
    monkeypatch.setattr("munk_device_web.device.sync_playwright", lambda: manager)
    return WebDevice(device_ref=device_ref, app_target=build_app_target(**launch_context)), page, browser_type


def test_web_device_screenshot_bgr_decodes_png(monkeypatch) -> None:
    device, _page, _browser_type = build_device(monkeypatch)

    image = device.screenshot_bgr()

    assert tuple(int(v) for v in image[0, 0]) == (1, 2, 3)


def test_web_device_click_and_scroll_delegate_to_mouse(monkeypatch) -> None:
    device, page, _browser_type = build_device(monkeypatch)

    device.click(12, 34)
    device.scroll((100, 200), (90, 150), duration=0.3)

    assert page.mouse.click_calls == [(12, 34)]
    assert page.mouse.move_calls == [(100, 200, None)]
    assert page.mouse.wheel_calls == [(10, 50)]


def test_web_device_drag_uses_mouse_drag_path(monkeypatch) -> None:
    device, page, _browser_type = build_device(monkeypatch)

    device.drag((100, 200), (260, 320), duration=0.5)

    assert page.mouse.move_calls == [
        (100, 200, None),
        (260, 320, 30),
    ]
    assert page.mouse.down_calls == 1
    assert page.mouse.up_calls == 1


def test_web_device_long_press_holds_mouse_button(monkeypatch) -> None:
    device, page, _browser_type = build_device(monkeypatch)
    sleep_calls: list[float] = []
    original_sleep = time.sleep

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("munk_device_web.device.time.sleep", fake_sleep)
    try:
        device.long_press(12, 34, duration=1.1)
    finally:
        monkeypatch.setattr("munk_device_web.device.time.sleep", original_sleep)

    assert page.mouse.move_calls == [(12, 34, None)]
    assert page.mouse.down_calls == 1
    assert page.mouse.up_calls == 1
    assert sleep_calls == [1.1]


def test_web_device_press_routes_back_home_and_keyboard(monkeypatch) -> None:
    device, page, _browser_type = build_device(monkeypatch)

    device.press("back")
    device.press("home")
    device.press("Enter")

    assert page.go_back_calls == ["domcontentloaded"]
    assert page.goto_calls[-1] == ("https://example.com/app", "domcontentloaded")
    assert page.keyboard.press_calls == ["Enter"]


def test_web_device_input_text_types_into_keyboard(monkeypatch) -> None:
    device, page, _browser_type = build_device(monkeypatch)

    device.input_text("hello web")

    assert page.keyboard.type_calls == ["hello web"]


def test_web_device_clear_text_clears_active_input(monkeypatch) -> None:
    device, page, _browser_type = build_device(monkeypatch)

    device.clear_text()

    assert page.active_text == ""
    assert page.keyboard.press_calls == []


def test_web_device_app_current_returns_structured_state(monkeypatch) -> None:
    device, page, _browser_type = build_device(monkeypatch)
    device.window_size()
    page.url = "https://example.com/settings/profile"
    page._title = "Profile"

    assert device.app_current() == CurrentAppState(
        platform="web",
        entry_identity="https://example.com",
        url="https://example.com/settings/profile",
        title="Profile",
        load_state="complete",
        raw={
            "url": "https://example.com/settings/profile",
            "title": "Profile",
            "load_state": "complete",
            "origin": "https://example.com",
            "surface_identity": "https://example.com/settings/profile",
        },
        surface_identity="https://example.com/settings/profile",
    )


def test_web_device_window_size_prefers_viewport(monkeypatch) -> None:
    device, _page, _browser_type = build_device(monkeypatch)

    assert device.window_size() == (1280, 720)


def test_web_device_capture_observation_tree_returns_web_dom(monkeypatch) -> None:
    device, page, _browser_type = build_device(monkeypatch)

    result = device.capture_observation_tree()

    assert result is not None
    assert result.source_type == "web_dom"
    assert result.content_type == "json"
    assert json.loads(result.payload) == page._dom_snapshot


def test_web_device_app_lifecycle_uses_base_url_for_reset(monkeypatch) -> None:
    device, page, _browser_type = build_device(monkeypatch)

    device.app_stop("https://example.com")
    device.app_start("https://example.com")

    assert page.goto_calls == [("https://example.com/app", "domcontentloaded")]


def test_web_device_runtime_logs_are_buffered_per_page(monkeypatch) -> None:
    device, page, _browser_type = build_device(monkeypatch)

    device.window_size()
    device.start_log_session()
    page.emit_console(message_type="error", text="boom")
    page.emit_console(message_type="warn", text="careful")

    entries = device.drain_runtime_logs()

    assert [entry.level for entry in entries] == ["error", "warning"]
    assert [entry.message for entry in entries] == ["boom", "careful"]
    assert entries[0].raw["page_url"] == "https://example.com/app"
    assert entries[0].raw["location"]["url"] == "https://example.com/app.js"
    assert device.drain_runtime_logs() == []


def test_web_device_runtime_logs_ignore_messages_before_session(monkeypatch) -> None:
    device, page, _browser_type = build_device(monkeypatch)

    device.window_size()
    page.emit_console(message_type="error", text="before start")
    device.start_log_session()
    page.emit_console(message_type="error", text="after start")
    device.stop_log_session()
    page.emit_console(message_type="error", text="after stop")

    assert device.drain_runtime_logs() == []


def test_web_device_new_page_resets_console_buffer(monkeypatch) -> None:
    device, page, _browser_type = build_device(monkeypatch)

    device.window_size()
    device.start_log_session()
    page.emit_console(message_type="error", text="before reset")
    assert [entry.message for entry in device.drain_runtime_logs()] == ["before reset"]

    device.app_start("https://example.com")
    new_page = cast(FakePage, device._page)  # type: ignore[attr-defined]
    new_page.emit_console(message_type="error", text="after reset")

    assert [entry.message for entry in device.drain_runtime_logs()] == ["after reset"]


def test_web_device_uses_cdp_when_device_ref_is_provided(monkeypatch) -> None:
    device, _page, browser_type = build_device(monkeypatch, device_ref="http://127.0.0.1:9222")

    device.window_size()

    assert browser_type.cdp_calls == ["http://127.0.0.1:9222"]
    assert browser_type.launch_calls == []


def test_web_device_launches_when_device_ref_is_logical_name(monkeypatch) -> None:
    device, _page, browser_type = build_device(monkeypatch, device_ref="web")

    device.window_size()

    assert browser_type.cdp_calls == []
    assert browser_type.launch_calls == [False]


def test_web_device_satisfies_protocols(monkeypatch) -> None:
    device, _page, _browser_type = build_device(monkeypatch)

    assert isinstance(cast(object, device), DeviceDriver)
    assert isinstance(cast(object, device), SupportsAppLifecycle)
    assert isinstance(cast(object, device), SupportsClose)
    assert isinstance(cast(object, device), SupportsRuntimeLogs)
    assert isinstance(cast(object, device), SupportsTextClear)
    assert isinstance(cast(object, device), SupportsElementTargetAction)


def test_web_device_fill_element_uses_value_fill_for_date(monkeypatch) -> None:
    device, page, _browser_type = build_device(monkeypatch)
    handle = {
        "kind": "dom",
        "selector": '[data-testid="due-date"]',
        "node_id": "node-1",
        "fill_mode": "value",
        "input_type": "date",
        "tag": "input",
    }

    device.fill_element(handle, "2025-05-15", mode="value")
    filled_locator = page.last_locator

    assert page.keyboard.type_calls == []
    assert filled_locator is not None
    assert filled_locator.fill_calls == ["2025-05-15"]
    assert filled_locator.input_value() == "2025-05-15"
    assert "input" in filled_locator.dispatch_calls
    assert "change" in filled_locator.dispatch_calls


def test_web_device_click_element_uses_locator(monkeypatch) -> None:
    device, page, _browser_type = build_device(monkeypatch)

    device.click_element({"kind": "dom", "selector": '[data-munk-node-id="node-0"]', "node_id": "node-0"})

    assert page.last_locator is not None
    assert page.last_locator.click_calls == 1
    assert page.mouse.click_calls == []


def test_web_device_close_releases_context_browser_and_playwright(monkeypatch) -> None:
    device, _page, _browser_type = build_device(monkeypatch)

    device.window_size()
    context = cast(FakeContext, device._context)  # type: ignore[attr-defined]
    browser = cast(FakeBrowser, device._browser)  # type: ignore[attr-defined]
    playwright = cast(FakePlaywright, device._playwright)  # type: ignore[attr-defined]

    device.close()

    assert context.closed is True
    assert browser.closed is True
    assert playwright.stopped is True
    assert device._context is None  # type: ignore[attr-defined]
    assert device._page is None  # type: ignore[attr-defined]
    assert device._browser is None  # type: ignore[attr-defined]
    assert device._playwright is None  # type: ignore[attr-defined]
    assert device._playwright_manager is None  # type: ignore[attr-defined]
    assert device._affinity.shut_down is True  # type: ignore[attr-defined]


def test_web_device_playwright_calls_run_on_owner_thread(monkeypatch) -> None:
    device, page, browser_type = build_device(monkeypatch)
    caller_ident = get_ident()
    owner_ident = device._affinity.owner_thread_ident  # type: ignore[attr-defined]
    assert caller_ident != owner_ident

    device.app_start("https://example.com")
    image = device.screenshot_bgr()
    browser = cast(FakeBrowser, device._browser)  # type: ignore[attr-defined]
    device.close()

    assert tuple(int(v) for v in image[0, 0]) == (1, 2, 3)
    assert browser_type.launch_thread_ids == [owner_ident]
    assert page.goto_thread_ids == [owner_ident]
    assert page.screenshot_thread_ids == [owner_ident]
    assert browser.close_thread_ids == [owner_ident]
    assert device._affinity.shut_down is True  # type: ignore[attr-defined]
