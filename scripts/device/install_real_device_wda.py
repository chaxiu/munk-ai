#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import plistlib
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from check_ios_wda_signing import (  # noqa: E402
    DEFAULT_IOS_SIGNING_ENV_FILE,
    CheckIOSWDASigningError,
    CheckIOSWDASigningResult,
    check_ios_wda_signing,
)
from install_wda_shared import (  # noqa: E402
    DEFAULT_WDA_URL,
    DEFAULT_WDA_VERSION,
    ROOT_DIR,
    CommandRunner,
    Downloader,
    InstallWDAError,
    InstallWDAResult,
    SleepFn,
    StatusChecker,
    default_command_runner,
    prepare_dependencies,
    print_result,
    wait_for_healthy,
)

DEFAULT_WDA_LOCAL_PORT = 8100
DEFAULT_WDA_REMOTE_PORT = 8100
DEFAULT_IPROXY_STARTUP_WAIT_SEC = 1.0
REAL_DEVICE_SOURCE_SUFFIX = "-real-device"
PBX_OBJECT_HEADER_TEMPLATE = r"^\s*{object_id} /\* .*? \*/ = \{{"
WEB_DRIVER_AGENT_LIB = "WebDriverAgentLib"
WEB_DRIVER_AGENT_RUNNER = "WebDriverAgentRunner"
XCTEST_RUNTIME_FRAMEWORK_PATTERNS = (
    "XC*.framework",
    "Testing.framework",
    "libXCTestSwiftSupport.dylib",
)


@dataclass(frozen=True)
class InstallRealDeviceWDAOptions:
    device_udid: str
    signing_env_file: Path = DEFAULT_IOS_SIGNING_ENV_FILE
    wda_version: str = DEFAULT_WDA_VERSION
    source_dir: Path | None = None
    force_download: bool = False
    force_rebuild: bool = False
    wda_local_port: int = DEFAULT_WDA_LOCAL_PORT
    wda_remote_port: int = DEFAULT_WDA_REMOTE_PORT
    wda_url: str = DEFAULT_WDA_URL


@dataclass(frozen=True)
class _NativeTargetInfo:
    target_id: str
    build_configuration_list_id: str
    build_configuration_ids: list[str]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download, build, install and launch WebDriverAgent for a real iOS device.")
    parser.add_argument("--device-udid", required=True, help="Connected iOS real-device UDID.")
    parser.add_argument("--signing-env-file", type=Path, default=DEFAULT_IOS_SIGNING_ENV_FILE, help="Signing env file for iOS real-device WDA build.")
    parser.add_argument("--wda-version", default=DEFAULT_WDA_VERSION, help=f"WDA git tag to download. Default: {DEFAULT_WDA_VERSION}")
    parser.add_argument("--source-dir", type=Path, default=None, help="Use an existing WDA source directory instead of downloading.")
    parser.add_argument("--force-download", action="store_true", help="Re-download and re-extract WDA sources.")
    parser.add_argument("--force-rebuild", action="store_true", help="Rebuild WDA even if a previous build output exists.")
    parser.add_argument("--wda-local-port", type=int, default=DEFAULT_WDA_LOCAL_PORT, help=f"Local forwarded port for WDA. Default: {DEFAULT_WDA_LOCAL_PORT}")
    parser.add_argument("--wda-remote-port", type=int, default=DEFAULT_WDA_REMOTE_PORT, help=f"Remote device WDA port. Default: {DEFAULT_WDA_REMOTE_PORT}")
    parser.add_argument("--wda-url", default=None, help="Optional override for WDA healthcheck URL. Defaults to the forwarded local port.")
    return parser


def parse_args(argv: list[str] | None = None) -> InstallRealDeviceWDAOptions:
    args = build_parser().parse_args(argv)
    local_wda_url = args.wda_url or f"http://127.0.0.1:{args.wda_local_port}"
    return InstallRealDeviceWDAOptions(
        device_udid=args.device_udid,
        signing_env_file=args.signing_env_file,
        wda_version=args.wda_version,
        source_dir=args.source_dir,
        force_download=bool(args.force_download),
        force_rebuild=bool(args.force_rebuild),
        wda_local_port=int(args.wda_local_port),
        wda_remote_port=int(args.wda_remote_port),
        wda_url=local_wda_url,
    )


def main(argv: list[str] | None = None) -> int:
    options = parse_args(argv)
    try:
        result = install_real_device_wda(options)
    except InstallWDAError as exc:
        result = InstallWDAResult(
            ok=False,
            stage=exc.stage,
            target_kind="real_device",
            wda_version=options.wda_version,
            device_udid=options.device_udid,
            wda_url=options.wda_url,
            local_wda_url=options.wda_url,
            signing_env_file=str(options.signing_env_file),
            message=exc.message,
        )
        print_result(result)
        return 1

    print_result(result)
    return 0


def install_real_device_wda(
    options: InstallRealDeviceWDAOptions,
    *,
    command_runner: CommandRunner | None = None,
    downloader: Downloader | None = None,
    status_checker: StatusChecker | None = None,
    sleep_fn: SleepFn | None = None,
) -> InstallWDAResult:
    run = command_runner or default_command_runner
    sleeper = sleep_fn or time.sleep
    _ensure_real_device_tooling(run)
    _ensure_iproxy_available(run)
    _ensure_real_device_available(options.device_udid, run)
    _ensure_real_device_developer_access(options.device_udid, run)
    signing_result = _check_signing(options.signing_env_file, run)
    signing_payload = _load_signing_payload(options.signing_env_file)
    signing_payload = _apply_selected_profile_defaults(signing_payload, signing_result)
    signing_payload = _apply_runner_profile_defaults(signing_payload, run)
    shared_source_dir = prepare_dependencies(
        wda_version=options.wda_version,
        source_dir=options.source_dir,
        force_download=options.force_download,
        command_runner=run,
        downloader=downloader,
    )
    source_dir = _prepare_real_device_source_dir(shared_source_dir)
    _configure_real_device_project(source_dir=source_dir, signing_payload=signing_payload)
    app_path, derived_data_path = _build_wda_for_real_device(
        source_dir=source_dir,
        options=options,
        command_runner=run,
    )
    _prepare_built_wda_for_real_device(
        app_path=app_path,
        signing_payload=signing_payload,
        command_runner=run,
    )
    _install_wda_app_on_real_device(options.device_udid, app_path, run)
    _launch_wda_runner_on_real_device(
        options.device_udid,
        _launch_bundle_id(signing_payload),
        run,
    )
    iproxy_pid = _start_iproxy(
        local_port=options.wda_local_port,
        remote_port=options.wda_remote_port,
        device_udid=options.device_udid,
        sleep_fn=sleeper,
    )
    wait_for_healthy(options.wda_url, status_checker=status_checker, sleep_fn=sleeper)
    return InstallWDAResult(
        ok=True,
        stage="completed",
        target_kind="real_device",
        wda_version=options.wda_version,
        source_dir=str(source_dir),
        device_udid=options.device_udid,
        wda_url=options.wda_url,
        local_wda_url=options.wda_url,
        app_path=str(app_path),
        derived_data_path=str(derived_data_path),
        iproxy_pid=iproxy_pid,
        signing_env_file=str(options.signing_env_file),
        message="WebDriverAgent is installed and healthy on the selected iOS real device.",
    )


def _ensure_real_device_tooling(command_runner: CommandRunner) -> None:
    try:
        command_runner(["xcrun", "devicectl", "--version"], True)
    except Exception as exc:  # noqa: BLE001
        raise InstallWDAError("environment_check_failed", f"required real-device tooling is unavailable: {exc}") from exc


def _ensure_iproxy_available(command_runner: CommandRunner) -> None:
    try:
        command_runner(["which", "iproxy"], True)
    except Exception as exc:  # noqa: BLE001
        raise InstallWDAError("port_forward_failed", f"iproxy is unavailable: {exc}") from exc


def _ensure_real_device_available(device_udid: str, command_runner: CommandRunner) -> None:
    try:
        payload_text = command_runner(["xcrun", "devicectl", "list", "devices", "--quiet", "--json-output", "-"], True)
    except Exception as exc:  # noqa: BLE001
        raise InstallWDAError("device_check_failed", f"failed to query iOS real devices: {exc}") from exc
    if payload_text is None:
        raise InstallWDAError("device_check_failed", "devicectl returned empty device list")
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise InstallWDAError("device_check_failed", f"devicectl returned invalid JSON: {exc}") from exc
    for entry in _find_device_dicts(payload):
        entry_udid = _lookup_string(entry, "identifier", "udid", "hardwareProperties.udid")
        if entry_udid != device_udid:
            continue
        state = (_lookup_string(entry, "connectionProperties.state", "state", "deviceProperties.bootState") or "").lower()
        if state in {"offline", "disconnected", "unavailable"}:
            raise InstallWDAError("device_check_failed", f"selected iOS real device is not available: {device_udid}")
        device_properties = entry.get("deviceProperties")
        if isinstance(device_properties, dict) and device_properties.get("ddiServicesAvailable") is False:
            pairing_state = _lookup_string(entry, "connectionProperties.pairingState") or "unknown"
            tunnel_state = _lookup_string(entry, "connectionProperties.tunnelState") or "unknown"
            raise InstallWDAError(
                "device_check_failed",
                (
                    "selected iOS real device is listed but developer services are unavailable: "
                    f"{device_udid} (pairingState={pairing_state}, tunnelState={tunnel_state}). "
                    "Unlock the device, trust this Mac, reconnect the USB cable, and open Xcode Devices and Simulators once."
                ),
            )
        return
    else:
        raise InstallWDAError("device_check_failed", f"selected iOS real device was not found: {device_udid}")


def _ensure_real_device_developer_access(device_udid: str, command_runner: CommandRunner) -> None:
    try:
        command_runner(
            ["xcrun", "devicectl", "device", "info", "lockState", "--device", device_udid, "--json-output", "-"],
            True,
        )
    except Exception as exc:  # noqa: BLE001
        raise InstallWDAError(
            "device_check_failed",
            (
                "selected iOS real device is not ready for developer services. "
                "Unlock the device, confirm trust prompts, reconnect the USB cable, "
                "and make sure Xcode Devices and Simulators can access it once. "
                f"Underlying error: {exc}"
            ),
        ) from exc


def _check_signing(signing_env_file: Path, command_runner: CommandRunner) -> CheckIOSWDASigningResult:
    try:
        result = check_ios_wda_signing(
            signing_env_file=signing_env_file,
            profile_dir=Path.home() / "Library" / "MobileDevice" / "Provisioning Profiles",
            command_runner=lambda command: _coerce_stdout(command_runner(command, True)),
        )
    except CheckIOSWDASigningError as exc:
        raise InstallWDAError("signing_check_failed", str(exc)) from exc
    if not result.ok:
        message = "; ".join(item.message for item in result.checks if not item.ok) or "iOS signing prerequisites are not satisfied"
        raise InstallWDAError("signing_check_failed", message)
    return result


def _apply_selected_profile_defaults(
    signing_payload: dict[str, str],
    signing_result: CheckIOSWDASigningResult,
) -> dict[str, str]:
    selected_profile = signing_result.selected_profile
    normalized = dict(signing_payload)
    if selected_profile is None:
        return normalized
    if not normalized.get("IOS_PROVISIONING_PROFILE_UUID") and selected_profile.uuid:
        normalized["IOS_PROVISIONING_PROFILE_UUID"] = selected_profile.uuid
    if not normalized.get("IOS_PROVISIONING_PROFILE_NAME") and selected_profile.name:
        normalized["IOS_PROVISIONING_PROFILE_NAME"] = selected_profile.name
    return normalized


def _apply_runner_profile_defaults(
    signing_payload: dict[str, str],
    command_runner: CommandRunner,
) -> dict[str, str]:
    normalized = dict(signing_payload)
    runner_profile_path_text = normalized.get("IOS_PROVISIONING_RUNNER_PROFILE_PATH")
    if not runner_profile_path_text:
        return normalized
    runner_profile_path = Path(runner_profile_path_text).expanduser().resolve()
    payload = _decode_mobileprovision(runner_profile_path, command_runner)
    name = payload.get("Name")
    uuid = payload.get("UUID")
    if not normalized.get("IOS_PROVISIONING_RUNNER_PROFILE_NAME") and isinstance(name, str):
        normalized["IOS_PROVISIONING_RUNNER_PROFILE_NAME"] = name
    if not normalized.get("IOS_PROVISIONING_RUNNER_PROFILE_UUID") and isinstance(uuid, str):
        normalized["IOS_PROVISIONING_RUNNER_PROFILE_UUID"] = uuid
    return normalized


def _load_signing_payload(signing_env_file: Path) -> dict[str, str]:
    payload: dict[str, str] = {}
    for raw_line in signing_env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        payload[key.strip()] = _strip_shell_quotes(value.strip())
    return payload


def _build_wda_for_real_device(
    *,
    source_dir: Path,
    options: InstallRealDeviceWDAOptions,
    command_runner: CommandRunner,
) -> tuple[Path, Path]:
    derived_data_path = source_dir.parent / "derived-data-real-device"
    app_path = derived_data_path / "Build" / "Products" / "Debug-iphoneos" / "WebDriverAgentRunner-Runner.app"
    if options.force_rebuild and derived_data_path.exists():
        shutil.rmtree(derived_data_path)
    if app_path.exists() and not options.force_rebuild:
        return app_path, derived_data_path

    project_path = source_dir / "WebDriverAgent.xcodeproj"
    if not project_path.exists():
        raise InstallWDAError("build_failed", f"WDA project file is missing: {project_path}")

    build_command = [
        "xcodebuild",
        "-project",
        str(project_path),
        "-scheme",
        "WebDriverAgentRunner",
        "-sdk",
        "iphoneos",
        "-destination",
        f"id={options.device_udid}",
        "-derivedDataPath",
        str(derived_data_path),
        "build-for-testing",
    ]
    try:
        command_runner(build_command, False)
    except Exception as exc:  # noqa: BLE001
        raise InstallWDAError("build_failed", f"failed to build WebDriverAgentRunner for real device: {exc}") from exc
    if not app_path.exists():
        raise InstallWDAError("build_failed", f"expected real-device build output is missing: {app_path}")
    return app_path, derived_data_path


def _install_wda_app_on_real_device(device_udid: str, app_path: Path, command_runner: CommandRunner) -> None:
    try:
        command_runner(
            ["xcrun", "devicectl", "device", "install", "app", "--device", device_udid, str(app_path)],
            False,
        )
    except Exception as exc:  # noqa: BLE001
        raise InstallWDAError("real_device_install_failed", f"failed to install WDA on real device: {exc}") from exc


def _prepare_built_wda_for_real_device(
    *,
    app_path: Path,
    signing_payload: dict[str, str],
    command_runner: CommandRunner,
) -> None:
    frameworks_dir = app_path / "Frameworks"
    for pattern in XCTEST_RUNTIME_FRAMEWORK_PATTERNS:
        for candidate in frameworks_dir.glob(pattern):
            if candidate.is_dir():
                shutil.rmtree(candidate)
            elif candidate.exists():
                candidate.unlink()
    xctest_bundle = app_path / "PlugIns" / "WebDriverAgentRunner.xctest"
    lib_framework = xctest_bundle / "Frameworks" / "WebDriverAgentLib.framework"
    identity = signing_payload["IOS_SIGNING_IDENTITY"]
    if lib_framework.exists():
        _codesign_bundle(lib_framework, identity=identity, command_runner=command_runner)
    if xctest_bundle.exists():
        _codesign_bundle(xctest_bundle, identity=identity, command_runner=command_runner)
    _codesign_bundle(app_path, identity=identity, command_runner=command_runner)
    _verify_codesign(app_path, command_runner=command_runner)


def _launch_wda_runner_on_real_device(device_udid: str, bundle_id: str, command_runner: CommandRunner) -> None:
    try:
        command_runner(
            ["xcrun", "devicectl", "device", "process", "launch", "--device", device_udid, bundle_id],
            False,
        )
    except Exception as exc:  # noqa: BLE001
        raise InstallWDAError("real_device_launch_failed", f"failed to launch WDA on real device: {exc}") from exc


def _start_iproxy(
    *,
    local_port: int,
    remote_port: int,
    device_udid: str,
    sleep_fn: SleepFn,
) -> int:
    process = subprocess.Popen(  # noqa: S603
        ["iproxy", f"{local_port}:{remote_port}", "-u", device_udid],
        cwd=ROOT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    sleep_fn(DEFAULT_IPROXY_STARTUP_WAIT_SEC)
    if process.poll() is not None:
        raise InstallWDAError("port_forward_failed", f"iproxy exited early for device {device_udid}")
    return int(process.pid)


def _launch_bundle_id(signing_payload: dict[str, str]) -> str:
    configured = signing_payload.get("IOS_WDA_LAUNCH_BUNDLE_ID")
    if configured:
        return configured
    return f"{signing_payload['IOS_WDA_BUNDLE_ID']}.xctrunner"


def _target_bundle_id(signing_payload: dict[str, str], *, target_name: str) -> str:
    _ = target_name
    return signing_payload["IOS_WDA_BUNDLE_ID"]


def _decode_mobileprovision(path: Path, command_runner: CommandRunner) -> dict[str, Any]:
    if not path.exists():
        raise InstallWDAError("signing_check_failed", f"runner provisioning profile does not exist: {path}")
    try:
        output = command_runner(["security", "cms", "-D", "-i", str(path)], True)
    except Exception as exc:  # noqa: BLE001
        raise InstallWDAError("signing_check_failed", f"failed to decode runner provisioning profile: {path}: {exc}") from exc
    if output is None:
        raise InstallWDAError("signing_check_failed", f"runner provisioning profile returned empty decode output: {path}")
    try:
        loaded = plistlib.loads(output.encode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise InstallWDAError("signing_check_failed", f"runner provisioning profile is not valid plist data: {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise InstallWDAError("signing_check_failed", f"runner provisioning profile has unexpected payload type: {path}")
    return loaded


def _codesign_bundle(path: Path, *, identity: str, command_runner: CommandRunner) -> None:
    try:
        command_runner(
            [
                "codesign",
                "--force",
                "--sign",
                identity,
                "--preserve-metadata=entitlements,requirements,flags",
                "--generate-entitlement-der",
                str(path),
            ],
            False,
        )
    except Exception as exc:  # noqa: BLE001
        raise InstallWDAError("build_failed", f"failed to re-sign WDA bundle: {path}: {exc}") from exc


def _verify_codesign(path: Path, *, command_runner: CommandRunner) -> None:
    try:
        command_runner(
            ["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(path)],
            False,
        )
    except Exception as exc:  # noqa: BLE001
        raise InstallWDAError("build_failed", f"failed to verify WDA signature: {path}: {exc}") from exc


def _coerce_stdout(value: str | None) -> str:
    if value is None:
        return ""
    return value


def _strip_shell_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _find_device_dicts(payload: Any) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    stack: list[Any] = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            maybe_udid = _lookup_string(current, "identifier", "udid", "hardwareProperties.udid")
            if maybe_udid is not None:
                results.append(current)
            stack.extend(current.values())
            continue
        if isinstance(current, list):
            stack.extend(current)
    return results


def _lookup_string(mapping: dict[str, Any], *paths: str) -> str | None:
    for path in paths:
        current: Any = mapping
        for segment in path.split("."):
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(segment)
        if current is None:
            continue
        if isinstance(current, str):
            return current
        return str(current)
    return None


def _prepare_real_device_source_dir(source_dir: Path) -> Path:
    working_source_dir = source_dir.parent / f"{source_dir.name}{REAL_DEVICE_SOURCE_SUFFIX}"
    if working_source_dir.exists():
        shutil.rmtree(working_source_dir)
    shutil.copytree(source_dir, working_source_dir)
    return working_source_dir


def _configure_real_device_project(*, source_dir: Path, signing_payload: dict[str, str]) -> None:
    project_path = source_dir / "WebDriverAgent.xcodeproj" / "project.pbxproj"
    if not project_path.exists():
        raise InstallWDAError("build_failed", f"WDA project file is missing: {project_path}")
    project_text = project_path.read_text(encoding="utf-8")
    lib_target = _load_native_target_info(project_text, WEB_DRIVER_AGENT_LIB)
    runner_target = _load_native_target_info(project_text, WEB_DRIVER_AGENT_RUNNER)
    project_text = _ensure_manual_provisioning_style(project_text, lib_target.target_id)
    project_text = _ensure_manual_provisioning_style(project_text, runner_target.target_id)
    for config_id in lib_target.build_configuration_ids:
        project_text = _rewrite_build_configuration(
            project_text,
            config_id=config_id,
            target_name=WEB_DRIVER_AGENT_LIB,
            signing_payload=signing_payload,
            include_profile=False,
        )
    for config_id in runner_target.build_configuration_ids:
        project_text = _rewrite_build_configuration(
            project_text,
            config_id=config_id,
            target_name=WEB_DRIVER_AGENT_RUNNER,
            signing_payload=signing_payload,
            include_profile=True,
        )
    project_path.write_text(project_text, encoding="utf-8")


def _load_native_target_info(project_text: str, target_name: str) -> _NativeTargetInfo:
    target_pattern = re.compile(
        rf"^\s*(?P<object_id>[A-F0-9]+) /\* {re.escape(target_name)} \*/ = \{{\n"
        r"\s*isa = PBXNativeTarget;\n"
        r"[\s\S]*?"
        r"\s*buildConfigurationList = (?P<config_list_id>[A-F0-9]+) /\* .*? \*/;",
        re.MULTILINE,
    )
    match = target_pattern.search(project_text)
    if match is None:
        raise InstallWDAError("build_failed", f"missing native target block in WDA project: {target_name}")
    target_id = match.group("object_id")
    config_list_id = match.group("config_list_id")
    config_list_object = _read_object_block(project_text, object_id=config_list_id)
    configuration_ids = re.findall(r"([A-F0-9]+) /\* [^*]+ \*/,", config_list_object["text"])
    if not configuration_ids:
        raise InstallWDAError("build_failed", f"missing build configurations for target {target_name}")
    return _NativeTargetInfo(
        target_id=target_id,
        build_configuration_list_id=config_list_id,
        build_configuration_ids=configuration_ids,
    )


def _ensure_manual_provisioning_style(project_text: str, target_id: str) -> str:
    target_attributes_bounds = _find_named_block(project_text, "TargetAttributes")
    if target_attributes_bounds is None:
        raise InstallWDAError("build_failed", "missing TargetAttributes block in WDA project")
    _, brace_open, brace_close, _ = target_attributes_bounds
    body = project_text[brace_open + 1 : brace_close]
    normalized_entry = f"\n\t\t\t\t{target_id} = {{\n\t\t\t\t\tProvisioningStyle = Manual;\n\t\t\t\t}};"
    entry_pattern = re.compile(rf"^\s*{re.escape(target_id)} = \{{[\s\S]*?^\s*\}};", re.MULTILINE)
    match = entry_pattern.search(body)
    if match is None:
        updated_body = body + normalized_entry
    else:
        if "ProvisioningStyle = Manual;" in match.group(0):
            return project_text
        updated_body = body[: match.start()] + normalized_entry + body[match.end() :]
    return project_text[: brace_open + 1] + updated_body + project_text[brace_close:]


def _rewrite_build_configuration(
    project_text: str,
    *,
    config_id: str,
    target_name: str,
    signing_payload: dict[str, str],
    include_profile: bool,
) -> str:
    config_object = _read_object_block(project_text, object_id=config_id)
    object_text = config_object["text"]
    build_settings_bounds = _find_named_block(object_text, "buildSettings")
    if build_settings_bounds is None:
        raise InstallWDAError("build_failed", f"missing buildSettings for {target_name} config {config_id}")
    _, brace_open, brace_close, _ = build_settings_bounds
    settings_text = object_text[brace_open + 1 : brace_close]
    settings_text = _upsert_scalar_setting(settings_text, "CODE_SIGN_STYLE", "Manual")
    settings_text = _upsert_scalar_setting(settings_text, "CODE_SIGN_IDENTITY", _pbx_quote(signing_payload["IOS_SIGNING_IDENTITY"]))
    settings_text = _upsert_scalar_setting(
        settings_text,
        '"CODE_SIGN_IDENTITY[sdk=iphoneos*]"',
        _pbx_quote(signing_payload["IOS_SIGNING_IDENTITY"]),
    )
    settings_text = _upsert_scalar_setting(settings_text, "DEVELOPMENT_TEAM", signing_payload["TEAM_ID"])
    settings_text = _upsert_scalar_setting(
        settings_text,
        '"DEVELOPMENT_TEAM[sdk=iphoneos*]"',
        signing_payload["TEAM_ID"],
    )
    settings_text = _upsert_scalar_setting(
        settings_text,
        "PRODUCT_BUNDLE_IDENTIFIER",
        _target_bundle_id(signing_payload, target_name=target_name),
    )
    if include_profile:
        profile_key, profile_value = _profile_build_setting(signing_payload, runner=True)
        settings_text = _remove_scalar_setting(settings_text, "PROVISIONING_PROFILE")
        settings_text = _remove_scalar_setting(settings_text, "PROVISIONING_PROFILE_SPECIFIER")
        settings_text = _upsert_scalar_setting(settings_text, profile_key, profile_value)
    else:
        settings_text = _remove_scalar_setting(settings_text, "PROVISIONING_PROFILE")
        settings_text = _remove_scalar_setting(settings_text, "PROVISIONING_PROFILE_SPECIFIER")
    updated_object = object_text[: brace_open + 1] + settings_text + object_text[brace_close:]
    return (
        project_text[: config_object["start"]]
        + updated_object
        + project_text[config_object["end"] :]
    )


def _profile_build_setting(signing_payload: dict[str, str], *, runner: bool = False) -> tuple[str, str]:
    if runner and signing_payload.get("IOS_PROVISIONING_RUNNER_PROFILE_UUID"):
        return "PROVISIONING_PROFILE", signing_payload["IOS_PROVISIONING_RUNNER_PROFILE_UUID"]
    if runner and signing_payload.get("IOS_PROVISIONING_RUNNER_PROFILE_NAME"):
        return "PROVISIONING_PROFILE_SPECIFIER", _pbx_quote(signing_payload["IOS_PROVISIONING_RUNNER_PROFILE_NAME"])
    if signing_payload.get("IOS_PROVISIONING_PROFILE_UUID"):
        return "PROVISIONING_PROFILE", signing_payload["IOS_PROVISIONING_PROFILE_UUID"]
    if signing_payload.get("IOS_PROVISIONING_PROFILE_NAME"):
        return "PROVISIONING_PROFILE_SPECIFIER", _pbx_quote(signing_payload["IOS_PROVISIONING_PROFILE_NAME"])
    raise InstallWDAError("signing_check_failed", "missing provisioning profile selector for manual real-device signing")


def _upsert_scalar_setting(settings_text: str, key: str, value: str) -> str:
    lines = settings_text.splitlines()
    updated_lines: list[str] = []
    replaced = False
    for line in lines:
        if _setting_key(line) == key:
            updated_lines.append(f"\t\t\t\t{key} = {value};")
            replaced = True
        else:
            updated_lines.append(line)
    if not replaced:
        updated_lines.append(f"\t\t\t\t{key} = {value};")
    return "\n".join(updated_lines) + ("\n" if settings_text.endswith("\n") or settings_text else "\n")


def _remove_scalar_setting(settings_text: str, key: str) -> str:
    lines = settings_text.splitlines()
    updated_lines = [line for line in lines if _setting_key(line) != key]
    return "\n".join(updated_lines) + ("\n" if settings_text.endswith("\n") or settings_text else "\n")


def _setting_key(line: str) -> str | None:
    if "=" not in line:
        return None
    stripped = line.strip()
    if not stripped or stripped.startswith(("(", ")", "{", "}")):
        return None
    return stripped.split("=", 1)[0].strip()


def _pbx_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _read_object_block(project_text: str, *, object_name: str | None = None, object_id: str | None = None) -> dict[str, Any]:
    if (object_name is None) == (object_id is None):
        raise InstallWDAError("build_failed", "exactly one of object_name or object_id must be provided")
    if object_name is not None:
        header_pattern = re.compile(
            rf"^\s*(?P<object_id>[A-F0-9]+) /\* {re.escape(object_name)} \*/ = \{{",
            re.MULTILINE,
        )
    else:
        header_pattern = re.compile(
            PBX_OBJECT_HEADER_TEMPLATE.format(object_id=re.escape(object_id or "")),
            re.MULTILINE,
        )
    match = header_pattern.search(project_text)
    if match is None:
        label = object_name if object_name is not None else object_id
        raise InstallWDAError("build_failed", f"missing object block in WDA project: {label}")
    resolved_object_id = match.groupdict().get("object_id", object_id)
    brace_open = project_text.find("{", match.start())
    brace_close = _find_matching_brace(project_text, brace_open)
    block_end = brace_close + 2 if project_text[brace_close + 1 : brace_close + 2] == ";" else brace_close + 1
    return {
        "id": resolved_object_id,
        "start": match.start(),
        "brace_open": brace_open,
        "brace_close": brace_close,
        "end": block_end,
        "text": project_text[match.start() : block_end],
    }


def _find_named_block(text: str, marker: str) -> tuple[int, int, int, int] | None:
    marker_index = text.find(f"{marker} = {{")
    if marker_index < 0:
        return None
    brace_open = text.find("{", marker_index)
    brace_close = _find_matching_brace(text, brace_open)
    block_end = brace_close + 2 if text[brace_close + 1 : brace_close + 2] == ";" else brace_close + 1
    return marker_index, brace_open, brace_close, block_end


def _find_matching_brace(text: str, brace_open: int) -> int:
    depth = 0
    for index in range(brace_open, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise InstallWDAError("build_failed", "unbalanced braces in WDA project file")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
