from __future__ import annotations

from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit

import httpx

DEFAULT_LOCAL_API_HOST = "127.0.0.1"
DEFAULT_LOCAL_API_PORT = 16888
DEFAULT_LOCAL_API_BASE_URL = f"http://{DEFAULT_LOCAL_API_HOST}:{DEFAULT_LOCAL_API_PORT}"


class LocalApiUnavailableError(RuntimeError):
    """Raised when the local API daemon cannot be reached."""


class LocalApiClient:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_LOCAL_API_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def submit(self, *, path: str, payload: dict[str, Any], wait: bool = True, detach: bool = False) -> dict[str, Any]:
        return self._request(
            method="POST",
            path=path,
            json_body=payload,
            params={"wait": str(wait).lower(), "detach": str(detach).lower()},
        )

    def review(self, *, payload: dict[str, Any], wait: bool = True, detach: bool = False) -> dict[str, Any]:
        return self.submit(path="/v1/review", payload=payload, wait=wait, detach=detach)

    def get_operation(self, *, operation_id: str) -> dict[str, Any]:
        return self._request(method="GET", path=f"/v1/runs/{operation_id}")

    def list_runs(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
        kind: str | None = None,
        device_ref: str | None = None,
        surface: str | None = None,
        verification_verdict: str | None = None,
        platform: str | None = None,
        query: str | None = None,
        run_type: str | None = None,
    ) -> dict[str, Any]:
        params = {"limit": str(limit), "offset": str(offset)}
        if status is not None:
            params["status"] = status
        if kind is not None:
            params["kind"] = kind
        if device_ref is not None:
            params["device_ref"] = device_ref
        if surface is not None:
            params["surface"] = surface
        if verification_verdict is not None:
            params["verification_verdict"] = verification_verdict
        if platform is not None:
            params["platform"] = platform
        if query is not None:
            params["query"] = query
        if run_type is not None:
            params["run_type"] = run_type
        return self._request(method="GET", path="/v1/runs", params=params)

    def get_dashboard_summary(self) -> dict[str, Any]:
        return self._request(method="GET", path="/v1/dashboard/summary")

    def search_cases(
        self,
        *,
        app_id: str | None = None,
        plan_id: str | None = None,
        case_id: str | None = None,
        is_core_case: bool | None = None,
        start_mode: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        params: dict[str, str] = {"limit": str(limit)}
        if app_id is not None:
            params["app_id"] = app_id
        if plan_id is not None:
            params["plan_id"] = plan_id
        if case_id is not None:
            params["case_id"] = case_id
        if is_core_case is not None:
            params["is_core_case"] = str(is_core_case).lower()
        if start_mode is not None:
            params["start_mode"] = start_mode
        return self._request(method="GET", path="/v1/plans/cases", params=params)

    def add_case(self, *, app_id: str, plan_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            method="POST",
            path=f"/v1/plans/{app_id}/{plan_id}/cases",
            json_body=payload,
        )

    def replace_case(self, *, app_id: str, plan_id: str, case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            method="PUT",
            path=f"/v1/plans/{app_id}/{plan_id}/cases/{case_id}/replace",
            json_body=payload,
        )

    def delete_case(self, *, app_id: str, plan_id: str, case_id: str) -> dict[str, Any]:
        return self._request(
            method="DELETE",
            path=f"/v1/plans/{app_id}/{plan_id}/cases/{case_id}",
        )

    def reorder_cases(self, *, app_id: str, plan_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            method="POST",
            path=f"/v1/plans/{app_id}/{plan_id}/cases:reorder",
            json_body=payload,
        )

    def list_events(self, *, operation_id: str, after_seq: int = 0, limit: int = 100) -> dict[str, Any]:
        return self._request(
            method="GET",
            path=f"/v1/runs/{operation_id}/events",
            params={"after_seq": str(after_seq), "limit": str(limit)},
        )

    def get_artifacts(self, *, operation_id: str) -> dict[str, Any]:
        return self._request(method="GET", path=f"/v1/runs/{operation_id}/artifacts")

    def get_artifact_content(
        self,
        *,
        operation_id: str,
        artifact_id: str,
        max_bytes: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, str] | None = None
        if max_bytes is not None:
            params = {"max_bytes": str(max_bytes)}
        return self._request(
            method="GET",
            path=f"/v1/runs/{operation_id}/artifacts/{artifact_id}/content",
            params=params,
        )

    def cancel(self, *, operation_id: str) -> dict[str, Any]:
        return self._request(method="POST", path=f"/v1/runs/{operation_id}/cancel")

    def reproduce(self, *, operation_id: str) -> dict[str, Any]:
        return self._request(method="POST", path=f"/v1/runs/{operation_id}/reproduce")

    def _request(
        self,
        *,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            with httpx.Client(timeout=self._timeout, trust_env=not _is_loopback_base_url(self._base_url)) as client:
                response = client.request(method, url, json=json_body, params=params)
        except httpx.HTTPError as exc:
            raise LocalApiUnavailableError(
                f"local api unavailable at {self._base_url}; please start it with `munk serve`"
            ) from exc
        return response.json()


def _is_loopback_base_url(base_url: str) -> bool:
    hostname = urlsplit(base_url).hostname
    if hostname is None:
        return False
    if hostname == "localhost":
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False
