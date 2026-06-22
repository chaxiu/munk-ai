from __future__ import annotations

from collections.abc import Callable

import httpx

from munk_device_ios import IOSBridgeClient, IOSBridgeSessionHandle

RequestHandler = Callable[[httpx.Request], httpx.Response]


def build_client(handler: RequestHandler) -> IOSBridgeClient:
    return IOSBridgeClient(
        session=IOSBridgeSessionHandle(
            base_url="http://127.0.0.1:17999",
            session_id="session-1",
            backend_kind="wda",
            device_udid="device-1",
        ),
        client=httpx.Client(
            base_url="http://127.0.0.1:17999",
            transport=httpx.MockTransport(handler),
        ),
    )


def test_bridge_client_parses_current_app_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/sessions/session-1/device/current-app"
        return httpx.Response(
            200,
            json={
                "ok": True,
                "data": {
                    "bundle_id": "com.example.demo",
                    "name": "Demo",
                    "pid": 42,
                    "raw": {"bundleId": "com.example.demo", "name": "Demo", "pid": 42},
                },
            },
        )

    client = build_client(handler)

    payload = client.current_app()

    assert payload.bundle_id == "com.example.demo"
    assert payload.name == "Demo"
    assert payload.pid == 42
    assert payload.raw["bundleId"] == "com.example.demo"


def test_bridge_client_parses_accessibility_tree_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/sessions/session-1/device/accessibility-tree"
        return httpx.Response(
            200,
            json={
                "ok": True,
                "data": {
                    "root": {
                        "type": "XCUIElementTypeApplication",
                        "name": "Demo",
                        "bundle_id": "com.example.demo",
                        "children": [
                            {
                                "type": "XCUIElementTypeButton",
                                "label": "Continue",
                                "rect": {"x": 10, "y": 20, "width": 100, "height": 44},
                                "children": [],
                            }
                        ],
                    }
                },
            },
        )

    client = build_client(handler)

    tree = client.accessibility_tree()

    assert tree is not None
    assert tree.root.node_type == "XCUIElementTypeApplication"
    assert tree.root.children[0].label == "Continue"
    assert tree.to_wda_payload() == {
        "type": "XCUIElementTypeApplication",
        "name": "Demo",
        "bundleId": "com.example.demo",
        "children": [
            {
                "type": "XCUIElementTypeButton",
                "label": "Continue",
                "rect": {"x": 10.0, "y": 20.0, "width": 100.0, "height": 44.0},
                "children": [],
            }
        ],
    }
