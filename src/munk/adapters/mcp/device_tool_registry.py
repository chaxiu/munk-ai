from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field

from munk.adapters.mcp.device_tool_handlers import DeviceMcpToolHandlers
from munk.adapters.mcp.device_tool_models import (
    AppInstallInput,
    AppLaunchInput,
    AppStopInput,
    DevicesListInput,
    SessionAbortInput,
    SessionActInput,
    SessionActionInput,
    SessionFinalizeInput,
    SessionGetInput,
    SessionObserveInput,
    SessionsListInput,
    SessionStartInput,
)
from munk.adapters.mcp.device_tool_outputs import (
    AppLifecycleOutput,
    DevicesListOutput,
    SessionAbortOutput,
    SessionActOutput,
    SessionFinalizeOutput,
    SessionGetOutput,
    SessionObserveOutput,
    SessionsListOutput,
    SessionStartOutput,
)


def register_device_mcp_tools(mcp: Any, handlers: DeviceMcpToolHandlers) -> None:
    @mcp.tool(
        name="devices_list",
        title="List Devices",
        description=(
            "List discovered local devices for a platform or across all supported runtimes.\n"
            "Use this before starting an interactive session when you need to inspect device availability.\n"
            "Returns the canonical discovered device payload.\n"
            "Does not claim or reserve any device."
        ),
        structured_output=True,
    )
    def devices_list(
        platform: Annotated[
            Literal["android", "ios", "web"] | None,
            Field(description="Optional platform filter: android, ios, or web."),
        ] = None,
    ) -> DevicesListOutput:
        return handlers.devices_list(DevicesListInput(platform=platform))

    @mcp.tool(
        name="app_launch",
        title="Launch App",
        description=(
            "Launch one application directly on a target device or runtime.\n"
            "Use this when an external agent needs to open or reset an app outside interactive session mode.\n"
            "Returns the resolved app identity and lifecycle action summary.\n"
            "Does not create a session, claim a device, or start an operation."
        ),
        structured_output=True,
    )
    def app_launch(
        app_id: Annotated[str, Field(description="Application identifier associated with the lifecycle action.")],
        platform: Annotated[
            Literal["android", "ios", "web"] | None,
            Field(description="Optional explicit platform override used to derive the app target."),
        ] = None,
        device_ref: Annotated[str | None, Field(description="Optional target device reference.")] = None,
        package: Annotated[str | None, Field(description="Optional Android package name override.")] = None,
        bundle_id: Annotated[str | None, Field(description="Optional iOS bundle identifier override.")] = None,
        base_url: Annotated[str | None, Field(description="Optional web base URL override.")] = None,
        origin: Annotated[str | None, Field(description="Optional web origin override.")] = None,
        headless: Annotated[bool, Field(description="Whether to launch the web runtime headlessly.")] = False,
        assets_root: Annotated[
            str | None,
            Field(description="Optional assets root containing apps/ and plans/ for app target resolution."),
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
        description=(
            "Stop one application directly on a target device or runtime.\n"
            "Use this when an external agent needs to terminate an app outside interactive session mode.\n"
            "Returns the resolved app identity and lifecycle action summary.\n"
            "Does not create a session, claim a device, or start an operation."
        ),
        structured_output=True,
    )
    def app_stop(
        app_id: Annotated[str, Field(description="Application identifier associated with the lifecycle action.")],
        platform: Annotated[
            Literal["android", "ios", "web"] | None,
            Field(description="Optional explicit platform override used to derive the app target."),
        ] = None,
        device_ref: Annotated[str | None, Field(description="Optional target device reference.")] = None,
        package: Annotated[str | None, Field(description="Optional Android package name override.")] = None,
        bundle_id: Annotated[str | None, Field(description="Optional iOS bundle identifier override.")] = None,
        base_url: Annotated[str | None, Field(description="Optional web base URL override.")] = None,
        origin: Annotated[str | None, Field(description="Optional web origin override.")] = None,
        headless: Annotated[bool, Field(description="Whether to launch the web runtime headlessly.")] = False,
        assets_root: Annotated[
            str | None,
            Field(description="Optional assets root containing apps/ and plans/ for app target resolution."),
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
        description=(
            "Install one application artifact directly on a target device.\n"
            "Use this before launch when the runtime supports installation; V1 schema is cross-platform but Android APK is the primary supported path, and artifact_path is a host workspace path that Android stages to /data/local/tmp before pm install.\n"
            "Returns the resolved app identity, artifact path, and lifecycle action summary.\n"
            "Does not create a session, claim a device, or start an operation."
        ),
        structured_output=True,
    )
    def app_install(
        app_id: Annotated[str, Field(description="Application identifier associated with the lifecycle action.")],
        artifact_path: Annotated[
            str,
            Field(description="Host workspace path to the application artifact to install. Android runtime stages it to a device tmp path before install."),
        ],
        platform: Annotated[
            Literal["android", "ios", "web"] | None,
            Field(description="Optional explicit platform override used to derive the app target."),
        ] = None,
        device_ref: Annotated[str | None, Field(description="Optional target device reference.")] = None,
        package: Annotated[str | None, Field(description="Optional Android package name override.")] = None,
        bundle_id: Annotated[str | None, Field(description="Optional iOS bundle identifier override.")] = None,
        base_url: Annotated[str | None, Field(description="Optional web base URL override.")] = None,
        origin: Annotated[str | None, Field(description="Optional web origin override.")] = None,
        headless: Annotated[bool, Field(description="Whether to launch the web runtime headlessly.")] = False,
        assets_root: Annotated[
            str | None,
            Field(description="Optional assets root containing apps/ and plans/ for app target resolution."),
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
                base_url=base_url,
                origin=origin,
                headless=headless,
                assets_root=Path(assets_root) if assets_root is not None else None,
            )
        )

    @mcp.tool(
        name="session_start",
        title="Start Session",
        description=(
            "Start one in-memory interactive device session.\n"
            "Use this when an external agent wants to iteratively observe and act on a device target; for Android, package is an optional override and session_start falls back to the app asset config when available.\n"
            "Returns the created session summary including session_id and expiry metadata.\n"
            "Does not create operations, artifacts, or persistent session storage."
        ),
        structured_output=True,
    )
    def session_start(
        app_id: Annotated[str, Field(description="Application identifier associated with the interactive session.")],
        platform: Annotated[
            Literal["android", "ios", "web"] | None,
            Field(description="Optional explicit platform override used to derive the app target."),
        ] = None,
        device_ref: Annotated[str | None, Field(description="Optional device reference to claim for the session.")] = None,
        package: Annotated[str | None, Field(description="Optional Android package name override.")] = None,
        bundle_id: Annotated[str | None, Field(description="Optional iOS bundle identifier override.")] = None,
        base_url: Annotated[str | None, Field(description="Optional web base URL override.")] = None,
        origin: Annotated[str | None, Field(description="Optional web origin override.")] = None,
        headless: Annotated[bool, Field(description="Whether to launch the web runtime headlessly.")] = False,
        config_path: Annotated[
            str | None,
            Field(description="Optional path to an existing config file in the workspace."),
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
        description=(
            "Load the current state of one interactive session by session_id.\n"
            "Use this to inspect status, expiry, and last observation summary between steps.\n"
            "Returns the canonical in-memory session summary.\n"
            "Does not capture a fresh observation or mutate the session."
        ),
        structured_output=True,
    )
    def session_get(
        session_id: Annotated[str, Field(description="Interactive session identifier.")],
    ) -> SessionGetOutput:
        return handlers.session_get(SessionGetInput(session_id=session_id))

    @mcp.tool(
        name="sessions_list",
        title="List Sessions",
        description=(
            "List active interactive sessions for recovery and troubleshooting.\n"
            "Use this when session_start reports a conflict or when an agent needs to resume an existing session.\n"
            "Returns active interactive session summaries with expiry and observation context.\n"
            "Does not include completed session history."
        ),
        structured_output=True,
    )
    def sessions_list(
        platform: Annotated[
            Literal["android", "ios", "web"] | None,
            Field(description="Optional platform filter for active interactive sessions."),
        ] = None,
        device_ref: Annotated[
            str | None,
            Field(description="Optional device reference filter for active interactive sessions."),
        ] = None,
        app_id: Annotated[
            str | None,
            Field(description="Optional app identifier filter for active interactive sessions."),
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
            "Capture one fresh observation for an interactive session.\n"
            "Use this when the agent needs the latest screen summary and action targets before deciding the next step.\n"
            "Returns the updated session summary and a compact observation payload by default; use detail=full for the complete payload.\n"
            "Set include_screenshot=true to include the same-frame observation screenshot as a saved PNG path using the session's default vl_max_side.\n"
            "Does not execute any action."
        ),
        structured_output=True,
    )
    def session_observe(
        session_id: Annotated[str, Field(description="Interactive session identifier to observe.")],
        detail: Annotated[
            Literal["compact", "full"],
            Field(description="Observation payload detail level. compact is the default agent-facing mode; full returns the complete payload."),
        ] = "compact",
        include_screenshot: Annotated[
            bool,
            Field(description="Whether to include the current observation screenshot as a saved PNG path. Disabled by default."),
        ] = False,
    ) -> SessionObserveOutput:
        return handlers.session_observe(
            SessionObserveInput(
                session_id=session_id,
                detail=detail,
                include_screenshot=include_screenshot,
            )
        )

    @mcp.tool(
        name="session_act",
        title="Act Session",
        description=(
            "Execute one allowed action inside an interactive session.\n"
            "Use this after an explicit observe step; prefer target_id from the latest session_observe result, with resource_id or label as fallbacks.\n"
            "Returns a compact action result by default; use detail=full for complete before and after observations, and optionally override the short post-action settle window before after is captured.\n"
            "Canonical example: {\"action\":{\"type\":\"click\",\"target_id\":12}}. Long-press example: {\"action\":{\"type\":\"long_press\",\"target_id\":12,\"duration\":1.2}}. Shorthand examples: {\"action\":{\"click\":12}}, {\"action\":{\"back\":true}}, {\"action\":{\"wait\":1.5}}.\n"
            "Does not run autonomous loops, retries, or judge-based convergence; box and point remain available as manual escape hatches."
        ),
        structured_output=True,
    )
    def session_act(
        session_id: Annotated[str, Field(description="Interactive session identifier to act on.")],
        action: Annotated[SessionActionInput, Field(description="One allowed interactive action request.")],
        detail: Annotated[
            Literal["compact", "full"],
            Field(description="Action result payload detail level. compact is the default agent-facing mode; full returns complete before/after observations."),
        ] = "compact",
        settle_timeout_sec: Annotated[
            float | None,
            Field(description="Optional post-action settle timeout in seconds. Defaults to 6.0 for interactive sessions."),
        ] = None,
    ) -> SessionActOutput:
        return handlers.session_act(
            SessionActInput(
                session_id=session_id,
                action=action,
                detail=detail,
                settle_timeout_sec=settle_timeout_sec,
            )
        )

    @mcp.tool(
        name="session_finalize",
        title="Finalize Session",
        description=(
            "Finalize one interactive session and build a transcript summary.\n"
            "Use this when the external agent is done with the device exploration loop.\n"
            "Returns the finalized session summary and transcript step summaries.\n"
            "Does not write reports, artifacts, or operation records."
        ),
        structured_output=True,
    )
    def session_finalize(
        session_id: Annotated[str, Field(description="Interactive session identifier to finalize.")],
        summary: Annotated[str | None, Field(description="Optional agent-authored summary attached to finalize result.")] = None,
    ) -> SessionFinalizeOutput:
        return handlers.session_finalize(SessionFinalizeInput(session_id=session_id, summary=summary))

    @mcp.tool(
        name="session_abort",
        title="Abort Session",
        description=(
            "Abort one active interactive session.\n"
            "Use this when the device loop should stop without producing a finalize transcript.\n"
            "Returns the aborted session summary.\n"
            "Does not persist the session or produce operation artifacts."
        ),
        structured_output=True,
    )
    def session_abort(
        session_id: Annotated[str, Field(description="Interactive session identifier to abort.")],
    ) -> SessionAbortOutput:
        return handlers.session_abort(SessionAbortInput(session_id=session_id))
