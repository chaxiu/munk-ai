from __future__ import annotations

import base64
import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from munk_device_ios import HttpWDAProvider

RequestHandler = Callable[[httpx.Request], httpx.Response]


def build_provider(handler: RequestHandler) -> HttpWDAProvider:
    client = httpx.Client(
        base_url="http://127.0.0.1:8100",
        transport=httpx.MockTransport(handler),
    )
    return HttpWDAProvider(client=client)


def read_json_body(request: httpx.Request) -> dict[str, Any]:
    if not request.content:
        return {}
    return json.loads(request.content.decode("utf-8"))


def test_session_routes_create_session_once_and_use_session_prefix() -> None:
    requests: list[tuple[str, str, dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = read_json_body(request)
        requests.append((request.method, request.url.path, body))
        if request.url.path == "/session":
            return httpx.Response(200, json={"value": {}, "sessionId": "sid-1"})
        if request.url.path == "/session/sid-1/wda/tap":
            return httpx.Response(200, json={"value": None})
        if request.url.path == "/session/sid-1/wda/touchAndHold":
            return httpx.Response(200, json={"value": None})
        if request.url.path == "/session/sid-1/wda/dragfromtoforduration":
            return httpx.Response(200, json={"value": None})
        if request.url.path == "/session/sid-1/wda/apps/launch":
            return httpx.Response(200, json={"value": None})
        if request.url.path == "/session/sid-1/wda/apps/terminate":
            return httpx.Response(200, json={"value": True})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    provider = build_provider(handler)

    provider.tap(12, 34)
    provider.long_press(12, 34, duration_sec=1.2)
    provider.swipe(start_x=10, start_y=20, end_x=100, end_y=200, duration_sec=0.5)
    provider.launch_app("com.example.demo")
    provider.terminate_app("com.example.demo")

    assert requests == [
        ("POST", "/session", {"capabilities": {"alwaysMatch": {}}}),
        ("POST", "/session/sid-1/wda/tap", {"x": 12, "y": 34}),
        ("POST", "/session/sid-1/wda/touchAndHold", {"x": 12, "y": 34, "duration": 1.2}),
        (
            "POST",
            "/session/sid-1/wda/dragfromtoforduration",
            {"fromX": 10, "fromY": 20, "toX": 100, "toY": 200, "duration": 0.5},
        ),
        ("POST", "/session/sid-1/wda/apps/launch", {"bundleId": "com.example.demo"}),
        ("POST", "/session/sid-1/wda/apps/terminate", {"bundleId": "com.example.demo"}),
    ]


def test_ensure_session_is_idempotent() -> None:
    requests: list[tuple[str, str, dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = read_json_body(request)
        requests.append((request.method, request.url.path, body))
        if request.url.path == "/session":
            return httpx.Response(200, json={"value": {}, "sessionId": "sid-1"})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    provider = build_provider(handler)

    provider.ensure_session()
    provider.ensure_session()

    assert requests == [("POST", "/session", {"capabilities": {"alwaysMatch": {}}})]


def test_read_only_routes_use_without_session_endpoints() -> None:
    requests: list[tuple[str, str, str]] = []
    screenshot_payload = base64.b64encode(b"png-bytes").decode("ascii")

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path, request.url.query.decode("utf-8")))
        if request.url.path == "/screenshot":
            return httpx.Response(200, json={"value": screenshot_payload})
        if request.url.path == "/wda/activeAppInfo":
            return httpx.Response(
                200,
                json={"value": {"bundleId": "com.example.demo", "name": "Demo"}},
            )
        if request.url.path == "/window/size":
            return httpx.Response(200, json={"value": {"width": 393, "height": 852}})
        if request.url.path == "/source":
            return httpx.Response(200, json={"value": {"type": "XCUIElementTypeApplication"}})
        if request.url.path == "/wda/homescreen":
            return httpx.Response(200, json={"value": None})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    provider = build_provider(handler)

    assert provider.screenshot_png() == b"png-bytes"
    assert provider.current_app().bundle_id == "com.example.demo"
    assert provider.window_size() == (393, 852)
    assert provider.accessibility_tree() is not None
    provider.press("home")

    assert requests == [
        ("GET", "/screenshot", ""),
        ("GET", "/wda/activeAppInfo", ""),
        ("GET", "/window/size", ""),
        ("GET", "/source", "format=json"),
        ("POST", "/wda/homescreen", ""),
    ]


def test_type_text_uses_session_keyboard_routes_and_ignores_dismiss_error() -> None:
    requests: list[tuple[str, str, dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = read_json_body(request)
        requests.append((request.method, request.url.path, body))
        if request.url.path == "/session":
            return httpx.Response(200, json={"value": {}, "sessionId": "sid-1"})
        if request.url.path == "/session/sid-1/wda/keyboard/dismiss":
            return httpx.Response(400, json={"value": {"message": "Keyboard not present"}})
        if request.url.path == "/session/sid-1/wda/keys":
            return httpx.Response(200, json={"value": None})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    provider = build_provider(handler)

    provider.type_text("hello")

    assert requests == [
        ("POST", "/session", {"capabilities": {"alwaysMatch": {}}}),
        ("POST", "/session/sid-1/wda/keyboard/dismiss", {"keyNames": []}),
        ("POST", "/session/sid-1/wda/keys", {"value": ["h", "e", "l", "l", "o"]}),
    ]


def test_clear_text_uses_active_element_and_clear_route() -> None:
    requests: list[tuple[str, str, dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = read_json_body(request)
        requests.append((request.method, request.url.path, body))
        if request.url.path == "/session":
            return httpx.Response(200, json={"value": {}, "sessionId": "sid-1"})
        if request.url.path == "/session/sid-1/element/active":
            return httpx.Response(
                200,
                json={"value": {"element-6066-11e4-a52e-4f735466cecf": "elem-1"}},
            )
        if request.url.path == "/session/sid-1/element/elem-1/clear":
            return httpx.Response(200, json={"value": None})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    provider = build_provider(handler)

    provider.clear_text()

    assert requests == [
        ("POST", "/session", {"capabilities": {"alwaysMatch": {}}}),
        ("GET", "/session/sid-1/element/active", {}),
        ("POST", "/session/sid-1/element/elem-1/clear", {}),
    ]


def test_dismiss_soft_keyboard_uses_session_route_and_ignores_error() -> None:
    requests: list[tuple[str, str, dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = read_json_body(request)
        requests.append((request.method, request.url.path, body))
        if request.url.path == "/session":
            return httpx.Response(200, json={"value": {}, "sessionId": "sid-1"})
        if request.url.path == "/session/sid-1/wda/keyboard/dismiss":
            return httpx.Response(400, json={"value": {"message": "Keyboard not present"}})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    provider = build_provider(handler)

    provider.dismiss_soft_keyboard()

    assert requests == [
        ("POST", "/session", {"capabilities": {"alwaysMatch": {}}}),
        ("POST", "/session/sid-1/wda/keyboard/dismiss", {"keyNames": []}),
    ]


def test_invalid_session_response_recreates_session_once() -> None:
    requests: list[tuple[str, str, dict[str, Any]]] = []
    session_ids = iter(["sid-1", "sid-2"])

    def handler(request: httpx.Request) -> httpx.Response:
        body = read_json_body(request)
        requests.append((request.method, request.url.path, body))
        if request.url.path == "/session":
            return httpx.Response(200, json={"value": {}, "sessionId": next(session_ids)})
        if request.url.path == "/session/sid-1/wda/apps/launch":
            return httpx.Response(
                404,
                json={"value": {"error": "invalid session id", "message": "Session does not exist"}},
            )
        if request.url.path == "/session/sid-2/wda/apps/launch":
            return httpx.Response(200, json={"value": None})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    provider = build_provider(handler)

    provider.launch_app("com.example.demo")

    assert requests == [
        ("POST", "/session", {"capabilities": {"alwaysMatch": {}}}),
        ("POST", "/session/sid-1/wda/apps/launch", {"bundleId": "com.example.demo"}),
        ("POST", "/session", {"capabilities": {"alwaysMatch": {}}}),
        ("POST", "/session/sid-2/wda/apps/launch", {"bundleId": "com.example.demo"}),
    ]


def test_create_session_requires_session_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/session":
            return httpx.Response(200, json={"value": {}})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    provider = build_provider(handler)

    with pytest.raises(ValueError, match="sessionId"):
        provider.launch_app("com.example.demo")


def test_close_deletes_existing_session() -> None:
    requests: list[tuple[str, str, dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = read_json_body(request)
        requests.append((request.method, request.url.path, body))
        if request.url.path == "/session":
            return httpx.Response(200, json={"value": {}, "sessionId": "sid-1"})
        if request.url.path == "/session/sid-1":
            return httpx.Response(200, json={"value": None})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    provider = build_provider(handler)

    provider.ensure_session()
    provider.close()

    assert requests == [
        ("POST", "/session", {"capabilities": {"alwaysMatch": {}}}),
        ("DELETE", "/session/sid-1", {}),
    ]


def test_close_ignores_missing_session_response_and_can_recreate() -> None:
    requests: list[tuple[str, str, dict[str, Any]]] = []
    session_ids = iter(["sid-1", "sid-2"])

    def handler(request: httpx.Request) -> httpx.Response:
        body = read_json_body(request)
        requests.append((request.method, request.url.path, body))
        if request.url.path == "/session":
            return httpx.Response(200, json={"value": {}, "sessionId": next(session_ids)})
        if request.url.path == "/session/sid-1":
            return httpx.Response(
                404,
                json={"value": {"error": "invalid session id", "message": "Session does not exist"}},
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    provider = build_provider(handler)

    provider.ensure_session()
    provider.close()
    provider.ensure_session()

    assert requests == [
        ("POST", "/session", {"capabilities": {"alwaysMatch": {}}}),
        ("DELETE", "/session/sid-1", {}),
        ("POST", "/session", {"capabilities": {"alwaysMatch": {}}}),
    ]
