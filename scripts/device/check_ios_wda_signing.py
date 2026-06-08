#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import plistlib
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, cast

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_IOS_SIGNING_ENV_FILE = Path("/Users/zhutao/.munk-release/ios_secrets.env")
DEFAULT_PROVISIONING_PROFILE_DIR = Path.home() / "Library" / "MobileDevice" / "Provisioning Profiles"

CommandRunner = Callable[[list[str]], str]


@dataclass(frozen=True)
class IOSSigningConfig:
    team_id: str
    bundle_id: str
    signing_identity: str
    provisioning_profile_name: str | None = None
    provisioning_profile_uuid: str | None = None
    provisioning_profile_path: Path | None = None


@dataclass(frozen=True)
class CheckItem:
    name: str
    ok: bool
    message: str


@dataclass(frozen=True)
class ProfileReport:
    path: str
    uuid: str | None
    name: str | None
    team_ids: list[str]
    application_identifier: str | None
    expiration_date: str | None
    expired: bool
    matched_selector: bool
    matched_team_id: bool
    matched_bundle_id: bool
    ok: bool


@dataclass(frozen=True)
class CheckIOSWDASigningResult:
    ok: bool
    env_file: str
    profile_dir: str
    config: dict[str, str | None]
    checks: list[CheckItem]
    selected_profile: ProfileReport | None
    candidate_profiles: list[ProfileReport]


class CheckIOSWDASigningError(RuntimeError):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check local iOS WDA signing prerequisites.")
    parser.add_argument("--signing-env-file", type=Path, default=DEFAULT_IOS_SIGNING_ENV_FILE)
    parser.add_argument("--profile-dir", type=Path, default=DEFAULT_PROVISIONING_PROFILE_DIR)
    parser.add_argument("--profile-file", type=Path, default=None)
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = check_ios_wda_signing(
            signing_env_file=args.signing_env_file,
            profile_dir=args.profile_dir,
            profile_file=args.profile_file,
        )
    except CheckIOSWDASigningError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "env_file": str(args.signing_env_file),
                    "profile_dir": str(args.profile_dir),
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.ok else 1


def check_ios_wda_signing(
    *,
    signing_env_file: Path,
    profile_dir: Path,
    profile_file: Path | None = None,
    command_runner: CommandRunner | None = None,
) -> CheckIOSWDASigningResult:
    run = command_runner or _default_command_runner
    config = _load_ios_signing_config(signing_env_file)
    if profile_file is not None:
        config = IOSSigningConfig(
            team_id=config.team_id,
            bundle_id=config.bundle_id,
            signing_identity=config.signing_identity,
            provisioning_profile_name=config.provisioning_profile_name,
            provisioning_profile_uuid=config.provisioning_profile_uuid,
            provisioning_profile_path=profile_file.expanduser().resolve(),
        )
    checks: list[CheckItem] = []

    checks.append(
        CheckItem(
            name="signing_env_file",
            ok=signing_env_file.exists(),
            message=(
                f"loaded signing env file: {signing_env_file}"
                if signing_env_file.exists()
                else f"signing env file does not exist: {signing_env_file}"
            ),
        )
    )

    if config.provisioning_profile_path is not None:
        profile_path_ok = config.provisioning_profile_path.exists()
        checks.append(
            CheckItem(
                name="provisioning_profile_path",
                ok=profile_path_ok,
                message=(
                    f"explicit provisioning profile exists: {config.provisioning_profile_path}"
                    if profile_path_ok
                    else f"explicit provisioning profile does not exist: {config.provisioning_profile_path}"
                ),
            )
        )

    identity_ok = _identity_exists(config.signing_identity, run)
    checks.append(
        CheckItem(
            name="signing_identity",
            ok=identity_ok,
            message=(
                f"codesigning identity is available in keychain: {config.signing_identity}"
                if identity_ok
                else f"codesigning identity was not found in keychain: {config.signing_identity}"
            ),
        )
    )

    profile_reports = _collect_profile_reports(config=config, profile_dir=profile_dir, command_runner=run)
    selected_profile = next((report for report in profile_reports if report.ok), None)
    if selected_profile is None:
        checks.append(
            CheckItem(
                name="provisioning_profile",
                ok=False,
                message=_build_profile_failure_message(config, profile_reports, profile_dir),
            )
        )
    else:
        checks.append(
            CheckItem(
                name="provisioning_profile",
                ok=True,
                message=(
                    f"matched provisioning profile: {selected_profile.name or selected_profile.uuid} "
                    f"({selected_profile.path})"
                ),
            )
        )

    ok = all(item.ok for item in checks)
    return CheckIOSWDASigningResult(
        ok=ok,
        env_file=str(signing_env_file),
        profile_dir=str(profile_dir),
        config={
            "TEAM_ID": config.team_id,
            "IOS_WDA_BUNDLE_ID": config.bundle_id,
            "IOS_SIGNING_IDENTITY": config.signing_identity,
            "IOS_PROVISIONING_PROFILE_NAME": config.provisioning_profile_name,
            "IOS_PROVISIONING_PROFILE_UUID": config.provisioning_profile_uuid,
            "IOS_PROVISIONING_PROFILE_PATH": str(config.provisioning_profile_path) if config.provisioning_profile_path else None,
        },
        checks=checks,
        selected_profile=selected_profile,
        candidate_profiles=profile_reports,
    )


def _load_ios_signing_config(signing_env_file: Path) -> IOSSigningConfig:
    env_payload = dict(os.environ)
    if signing_env_file.exists():
        env_payload.update(_parse_env_file(signing_env_file))
    required = ["TEAM_ID", "IOS_WDA_BUNDLE_ID", "IOS_SIGNING_IDENTITY"]
    missing = [key for key in required if not env_payload.get(key)]
    if missing:
        raise CheckIOSWDASigningError(
            f"missing iOS signing settings in {signing_env_file}: {', '.join(missing)}"
        )
    if not env_payload.get("IOS_PROVISIONING_PROFILE_NAME") and not env_payload.get("IOS_PROVISIONING_PROFILE_UUID"):
        if not env_payload.get("IOS_PROVISIONING_PROFILE_PATH"):
            raise CheckIOSWDASigningError(
                "one of IOS_PROVISIONING_PROFILE_NAME, IOS_PROVISIONING_PROFILE_UUID or IOS_PROVISIONING_PROFILE_PATH is required"
            )
    return IOSSigningConfig(
        team_id=env_payload["TEAM_ID"],
        bundle_id=env_payload["IOS_WDA_BUNDLE_ID"],
        signing_identity=env_payload["IOS_SIGNING_IDENTITY"],
        provisioning_profile_name=env_payload.get("IOS_PROVISIONING_PROFILE_NAME"),
        provisioning_profile_uuid=env_payload.get("IOS_PROVISIONING_PROFILE_UUID"),
        provisioning_profile_path=(
            Path(env_payload["IOS_PROVISIONING_PROFILE_PATH"]).expanduser().resolve()
            if env_payload.get("IOS_PROVISIONING_PROFILE_PATH")
            else None
        ),
    )


def _parse_env_file(path: Path) -> dict[str, str]:
    payload: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        payload[key] = _strip_shell_quotes(value)
    return payload


def _strip_shell_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _identity_exists(signing_identity: str, command_runner: CommandRunner) -> bool:
    try:
        output = command_runner(["security", "find-identity", "-v", "-p", "codesigning"])
    except Exception:
        return False
    return signing_identity in output


def _collect_profile_reports(
    *,
    config: IOSSigningConfig,
    profile_dir: Path,
    command_runner: CommandRunner,
) -> list[ProfileReport]:
    reports: list[ProfileReport] = []
    if config.provisioning_profile_path is not None:
        payload = _decode_mobileprovision(config.provisioning_profile_path, command_runner)
        if payload is None:
            return []
        return [_build_profile_report(path=config.provisioning_profile_path, payload=payload, config=config)]
    if not profile_dir.exists():
        return []
    for path in sorted(profile_dir.glob("*.mobileprovision")):
        payload = _decode_mobileprovision(path, command_runner)
        if payload is None:
            continue
        reports.append(_build_profile_report(path=path, payload=payload, config=config))
    return reports


def _decode_mobileprovision(path: Path, command_runner: CommandRunner) -> dict[str, Any] | None:
    try:
        output = command_runner(["security", "cms", "-D", "-i", str(path)])
    except Exception:
        return None
    loaded = cast(object, plistlib.loads(output.encode("utf-8")))
    if not isinstance(loaded, dict):
        return None
    return cast(dict[str, Any], loaded)


def _build_profile_report(
    *,
    path: Path,
    payload: dict[str, Any],
    config: IOSSigningConfig,
) -> ProfileReport:
    name = payload.get("Name") if isinstance(payload.get("Name"), str) else None
    uuid = payload.get("UUID") if isinstance(payload.get("UUID"), str) else None
    team_ids = [str(item) for item in payload.get("TeamIdentifier", []) if isinstance(item, str)]
    entitlements = payload.get("Entitlements")
    if isinstance(entitlements, dict):
        app_identifier = cast(dict[str, Any], entitlements).get("application-identifier")
    else:
        app_identifier = None
    if not isinstance(app_identifier, str):
        app_identifier = None
    expiration_value = payload.get("ExpirationDate")
    expiration_date = expiration_value if isinstance(expiration_value, datetime) else None
    expired = expiration_date is not None and expiration_date.astimezone(timezone.utc) <= datetime.now(timezone.utc)
    matched_selector = _profile_matches_selector(
        name=name,
        uuid=uuid,
        expected_name=config.provisioning_profile_name,
        expected_uuid=config.provisioning_profile_uuid,
    )
    matched_team_id = config.team_id in team_ids
    matched_bundle_id = _bundle_id_matches_application_identifier(
        team_id=config.team_id,
        bundle_id=config.bundle_id,
        application_identifier=app_identifier,
    )
    ok = matched_selector and matched_team_id and matched_bundle_id and not expired
    return ProfileReport(
        path=str(path),
        uuid=uuid,
        name=name,
        team_ids=team_ids,
        application_identifier=app_identifier,
        expiration_date=expiration_date.isoformat() if expiration_date is not None else None,
        expired=expired,
        matched_selector=matched_selector,
        matched_team_id=matched_team_id,
        matched_bundle_id=matched_bundle_id,
        ok=ok,
    )


def _profile_matches_selector(
    *,
    name: str | None,
    uuid: str | None,
    expected_name: str | None,
    expected_uuid: str | None,
) -> bool:
    if expected_uuid:
        return uuid == expected_uuid
    if expected_name is None and expected_uuid is None:
        return True
    if expected_name:
        return name == expected_name
    return False


def _bundle_id_matches_application_identifier(
    *,
    team_id: str,
    bundle_id: str,
    application_identifier: str | None,
) -> bool:
    if not application_identifier:
        return False
    prefix = f"{team_id}."
    if not application_identifier.startswith(prefix):
        return False
    pattern = application_identifier[len(prefix) :]
    if pattern == "*":
        return True
    if "*" not in pattern:
        return pattern == bundle_id
    parts = pattern.split("*")
    cursor = 0
    if not pattern.startswith("*"):
        first = parts.pop(0)
        if not bundle_id.startswith(first):
            return False
        cursor = len(first)
    if not pattern.endswith("*"):
        last = parts.pop() if parts else ""
        if not bundle_id.endswith(last):
            return False
        tail_limit = len(bundle_id) - len(last)
    else:
        tail_limit = len(bundle_id)
    for part in parts:
        if not part:
            continue
        next_index = bundle_id.find(part, cursor, tail_limit)
        if next_index < 0:
            return False
        cursor = next_index + len(part)
    return cursor <= tail_limit


def _build_profile_failure_message(
    config: IOSSigningConfig,
    profile_reports: list[ProfileReport],
    profile_dir: Path,
) -> str:
    if config.provisioning_profile_path is not None:
        if not config.provisioning_profile_path.exists():
            return f"explicit provisioning profile does not exist: {config.provisioning_profile_path}"
        if not profile_reports:
            return f"explicit provisioning profile could not be decoded: {config.provisioning_profile_path}"
    selector = config.provisioning_profile_uuid or config.provisioning_profile_name or "<unknown>"
    selected_candidates = [report for report in profile_reports if report.matched_selector]
    if not profile_reports:
        return f"no decodable provisioning profiles were found in {profile_dir}"
    if not selected_candidates:
        return f"provisioning profile was not found: {selector}"
    reasons: list[str] = []
    if not any(report.matched_team_id for report in selected_candidates):
        reasons.append(f"TEAM_ID {config.team_id} does not match selected profile")
    if not any(report.matched_bundle_id for report in selected_candidates):
        reasons.append(f"IOS_WDA_BUNDLE_ID {config.bundle_id} is not covered by selected profile")
    if any(report.expired for report in selected_candidates):
        reasons.append("selected profile is expired")
    return "; ".join(reasons) if reasons else "selected profile failed validation"


def _default_command_runner(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        check=True,
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )
    return completed.stdout


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
