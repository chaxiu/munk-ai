from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from mcp.types import CallToolResult
from pydantic import Field

from munk.adapters.mcp.device_tool_handlers import DeviceMcpToolHandlers
from munk.adapters.mcp.device_tool_models import (
    AppInstallInput,
    AppLaunchInput,
    AppStopInput,
    DevicesListInput,
    DeviceStateInput,
    DeviceUnlockInput,
    SessionAbortInput,
    SessionActInput,
    SessionActionInput,
    SessionFinalizeInput,
    SessionGetInput,
    SessionListTargetsInput,
    SessionObserveInput,
    SessionsListInput,
    SessionStartInput,
)
from munk.adapters.mcp.device_tool_outputs import (
    AppLifecycleOutput,
    DevicesListOutput,
    DeviceStateOutput,
    DeviceUnlockOutput,
    SessionAbortOutput,
    SessionActOutput,
    SessionFinalizeOutput,
    SessionGetOutput,
    SessionListTargetsOutput,
    SessionObserveOutput,
    SessionsListOutput,
    SessionStartOutput,
)
from munk.adapters.mcp.device_tool_results import build_session_observe_call_tool_result


def register_device_mcp_tools(mcp: Any, handlers: DeviceMcpToolHandlers) -> None:  # noqa: C901
    @mcp.tool(
        name="devices_list",
        title="List Devices",
        description="List discovered local devices. Optional platform filter.",
        structured_output=True,
    )
    def devices_list(
        platform: Annotated[
            Literal["android", "ios", "web"] | None,
            Field(description="Optional platform filter."),
        ] = None,
    ) -> DevicesListOutput:
        return handlers.devices_list(DevicesListInput(platform=platform))

    @mcp.tool(
        name="device_state",
        title="Get Device State",
        description="Read lock, screen, and automation readiness for one device.",
        structured_output=True,
    )
    def device_state(
        device_ref: Annotated[str, Field(description="Device reference.")],
        platform: Annotated[
            Literal["android", "ios", "web"] | None,
            Field(description="Optional platform disambiguator."),
        ] = None,
    ) -> DeviceStateOutput:
        return handlers.device_state(DeviceStateInput(device_ref=device_ref, platform=platform))

    @mcp.tool(
        name="device_unlock",
        title="Unlock Device",
        description="Unlock one device. V1: Android swipe only.",
        structured_output=True,
    )
    def device_unlock(
        device_ref: Annotated[str, Field(description="Device reference.")],
        platform: Annotated[
            Literal["android", "ios", "web"] | None,
            Field(description="Optional platform disambiguator."),
        ] = None,
        strategy: Annotated[
            Literal["swipe"],
            Field(description="Unlock strategy. V1: swipe only."),
        ] = "swipe",
    ) -> DeviceUnlockOutput:
        return handlers.device_unlock(DeviceUnlockInput(device_ref=device_ref, platform=platform, strategy=strategy))

    @mcp.tool(
        name="app_launch",
        title="Launch App",
        description="Launch an app outside an interactive session.",
        structured_output=True,
    )
    def app_launch(
        app_id: Annotated[str, Field(description="App identifier.")],
        platform: Annotated[
            Literal["android", "ios", "web"] | None,
            Field(description="Optional platform override."),
        ] = None,
        device_ref: Annotated[str | None, Field(description="Optional device reference.")] = None,
        package: Annotated[str | None, Field(description="Optional Android package.")] = None,
        bundle_id: Annotated[str | None, Field(description="Optional iOS bundle id.")] = None,
        base_url: Annotated[str | None, Field(description="Optional web base URL.")] = None,
        origin: Annotated[str | None, Field(description="Optional web origin.")] = None,
        headless: Annotated[bool, Field(description="Launch web runtime headlessly.")] = False,
        assets_root: Annotated[
            str | None,
            Field(description="Optional assets root (apps/, plans/)."),
        ] = None,
    ) -> AppLifecycleOutput:
        return handlers.app_launch(
            AppLaunchInput(
                app_id=app_id,
                platform=platform,
                device_ref=device_ref,
                package=package,
                bundle_id=bundle_id,
                base_url=base_url,
                origin=origin,
                headless=headless,
                assets_root=Path(assets_root) if assets_root is not None else None,
            )
        )

    @mcp.tool(
        name="app_stop",
        title="Stop App",
        description="Stop an app outside an interactive session.",
        structured_output=True,
    )
    def app_stop(
        app_id: Annotated[str, Field(description="App identifier.")],
        platform: Annotated[
            Literal["android", "ios", "web"] | None,
            Field(description="Optional platform override."),
        ] = None,
        device_ref: Annotated[str | None, Field(description="Optional device reference.")] = None,
        package: Annotated[str | None, Field(description="Optional Android package.")] = None,
        bundle_id: Annotated[str | None, Field(description="Optional iOS bundle id.")] = None,
        base_url: Annotated[str | None, Field(description="Optional web base URL.")] = None,
        origin: Annotated[str | None, Field(description="Optional web origin.")] = None,
        headless: Annotated[bool, Field(description="Launch web runtime headlessly.")] = False,
        assets_root: Annotated[
            str | None,
            Field(description="Optional assets root (apps/, plans/)."),
        ] = None,
    ) -> AppLifecycleOutput:
        return handlers.app_stop(
            AppStopInput(
                app_id=app_id,
                platform=platform,
                device_ref=device_ref,
                package=package,
                bundle_id=bundle_id,
                base_url=base_url,
                origin=origin,
                headless=headless,
                assets_root=Path(assets_root) if assets_root is not None else None,
            )
        )

    @mcp.tool(
        name="app_install",
        title="Install App",
        description="Install an app artifact. V1 Android-primary (package + artifact_path); web fields not accepted.",
        structured_output=True,
    )
    def app_install(
        app_id: Annotated[str, Field(description="App identifier.")],
        artifact_path: Annotated[
            str,
            Field(description="Host path to the install artifact."),
        ],
        platform: Annotated[
            Literal["android", "ios", "web"] | None,
            Field(description="Optional platform override. V1 install is Android-primary."),
        ] = None,
        device_ref: Annotated[str | None, Field(description="Optional device reference.")] = None,
        package: Annotated[str | None, Field(description="Optional Android package.")] = None,
        bundle_id: Annotated[
            str | None,
            Field(description="Optional iOS bundle id (not V1 primary)."),
        ] = None,
        assets_root: Annotated[
            str | None,
            Field(description="Optional assets root (apps/, plans/)."),
        ] = None,
    ) -> AppLifecycleOutput:
        return handlers.app_install(
            AppInstallInput(
                app_id=app_id,
                artifact_path=Path(artifact_path),
                platform=platform,
                device_ref=device_ref,
                package=package,
                bundle_id=bundle_id,
                assets_root=Path(assets_root) if assets_root is not None else None,
            )
        )

    @mcp.tool(
        name="session_start",
        title="Start Session",
        description=(
            "Start an interactive session (debug clients). "
            "Auto smoke should use Local API POST /v1/interactive/sessions. "
            "Conflicts include JSON recovery guidance."
        ),
        structured_output=True,
    )
    def session_start(
        app_id: Annotated[str, Field(description="App identifier.")],
        platform: Annotated[
            Literal["android", "ios", "web"] | None,
            Field(description="Optional platform override."),
        ] = None,
        device_ref: Annotated[str | None, Field(description="Optional device to claim.")] = None,
        package: Annotated[str | None, Field(description="Optional Android package.")] = None,
        bundle_id: Annotated[str | None, Field(description="Optional iOS bundle id.")] = None,
        base_url: Annotated[str | None, Field(description="Optional web base URL.")] = None,
        origin: Annotated[str | None, Field(description="Optional web origin.")] = None,
        headless: Annotated[bool, Field(description="Launch web runtime headlessly.")] = False,
        config_path: Annotated[
            str | None,
            Field(description="Optional workspace config path."),
        ] = None,
    ) -> SessionStartOutput:
        resolved_config_path = Path(config_path) if config_path is not None else None
        return handlers.session_start(
            SessionStartInput.model_validate(
                {
                    "app_id": app_id,
                    "platform": platform,
                    "device_ref": device_ref,
                    "package": package,
                    "bundle_id": bundle_id,
                    "base_url": base_url,
                    "origin": origin,
                    "headless": headless,
                    "config_path": resolved_config_path,
                }
            )
        )

    @mcp.tool(
        name="session_get",
        title="Get Session",
        description="Load one interactive session by session_id.",
        structured_output=True,
    )
    def session_get(
        session_id: Annotated[str, Field(description="Session id.")],
    ) -> SessionGetOutput:
        return handlers.session_get(SessionGetInput(session_id=session_id))

    @mcp.tool(
        name="sessions_list",
        title="List Sessions",
        description="List active interactive sessions for recovery.",
        structured_output=True,
    )
    def sessions_list(
        platform: Annotated[
            Literal["android", "ios", "web"] | None,
            Field(description="Optional platform filter."),
        ] = None,
        device_ref: Annotated[
            str | None,
            Field(description="Optional device filter."),
        ] = None,
        app_id: Annotated[
            str | None,
            Field(description="Optional app filter."),
        ] = None,
    ) -> SessionsListOutput:
        return handlers.sessions_list(
            SessionsListInput(
                platform=platform,
                device_ref=device_ref,
                app_id=app_id,
            )
        )

    @mcp.tool(
        name="session_observe",
        title="Observe Session",
        description=(
            "Capture a fresh observation with Runner-style targets_text (#vN/#tN). "
            "If truncated, page via session_list_targets on the same snapshot. "
            "Optional match bypass; include_screenshot=true returns an MCP image block."
        ),
        structured_output=True,
    )
    def session_observe(
        session_id: Annotated[str, Field(description="Session id.")],
        match: Annotated[
            str | None,
            Field(description="Keyword bypass hit region; does not rewrite targets_text."),
        ] = None,
        include_screenshot: Annotated[
            bool,
            Field(description="Return an MCP image block (vision). Default false."),
        ] = False,
    ) -> Annotated[CallToolResult, SessionObserveOutput]:
        return build_session_observe_call_tool_result(
            handlers.session_observe(
                SessionObserveInput(
                    session_id=session_id,
                    match=match,
                    include_screenshot=include_screenshot,
                )
            )
        )

    @mcp.tool(
        name="session_list_targets",
        title="List Session Targets",
        description=(
            "Page targets from the last observation without re-capturing. "
            "Requires prior session_observe."
        ),
        structured_output=True,
    )
    def session_list_targets(
        session_id: Annotated[
            str,
            Field(description="Session id."),
        ],
        source: Annotated[
            Literal["all", "vision", "tree"],
            Field(description="Channel filter. all applies offset/limit per channel."),
        ] = "all",
        offset: Annotated[int, Field(description="Pagination offset per channel.", ge=0)] = 0,
        limit: Annotated[
            int | None,
            Field(description="Page size. Default 40."),
        ] = None,
    ) -> SessionListTargetsOutput:
        return handlers.session_list_targets(
            SessionListTargetsInput(
                session_id=session_id,
                source=source,
                offset=offset,
                limit=limit,
            )
        )

    @mcp.tool(
        name="session_act",
        title="Act Session",
        description=(
            "Execute one action after observe. Prefer #vN/#tN from targets_text or match.match_text. "
            "set_value needs tN + value; edit_text uses text. Returns a fixed summary."
        ),
        structured_output=True,
    )
    def session_act(
        session_id: Annotated[str, Field(description="Session id.")],
        action: Annotated[SessionActionInput, Field(description="One action request.")],
        timeout_sec: Annotated[
            float | None,
            Field(description="Post-action settle timeout seconds. Default 6."),
        ] = None,
    ) -> SessionActOutput:
        return handlers.session_act(
            SessionActInput(
                session_id=session_id,
                action=action,
                timeout_sec=timeout_sec,
            )
        )

    @mcp.tool(
        name="session_finalize",
        title="Finalize Session",
        description="Finalize a session and return a transcript summary.",
        structured_output=True,
    )
    def session_finalize(
        session_id: Annotated[str, Field(description="Session id.")],
        summary: Annotated[str | None, Field(description="Optional agent summary.")] = None,
    ) -> SessionFinalizeOutput:
        return handlers.session_finalize(SessionFinalizeInput(session_id=session_id, summary=summary))

    @mcp.tool(
        name="session_abort",
        title="Abort Session",
        description="Abort a session without a finalize transcript.",
        structured_output=True,
    )
    def session_abort(
        session_id: Annotated[str, Field(description="Session id.")],
    ) -> SessionAbortOutput:
        return handlers.session_abort(SessionAbortInput(session_id=session_id))
