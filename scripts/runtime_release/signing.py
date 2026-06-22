from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

ROOT_DIR = Path(__file__).resolve().parents[2]
NODE_JIT_ENTITLEMENTS_PATH = ROOT_DIR / "scripts" / "node_jit_entitlements.plist"
MACHO_MAGIC_NUMBERS = {
    b"\xfe\xed\xfa\xce",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
    b"\xca\xfe\xba\xbf",
    b"\xbf\xba\xfe\xca",
}


class NotarizationResult(TypedDict, total=False):
    submission_id: str
    status: str
    message: str
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class ReleaseSigningConfig:
    team_id: str
    bundle_id: str
    signing_identity: str
    asc_key_id: str
    asc_issuer_id: str
    asc_key_path: Path
    p12_path: Path | None = None
    p12_password: str | None = None


@dataclass(frozen=True)
class KeychainSession:
    path: Path
    password: str
    temp_dir: Path


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


def _load_release_signing_config(signing_env_file: Path) -> ReleaseSigningConfig:
    env_payload = dict(os.environ)
    if signing_env_file.exists():
        env_payload.update(_parse_env_file(signing_env_file))
    elif not _has_release_signing_env(env_payload):
        raise RuntimeError(f"missing signing env file: {signing_env_file}")
    return _validate_signing_config(env_payload, signing_env_file)


def _has_release_signing_env(payload: dict[str, str]) -> bool:
    required = {
        "TEAM_ID",
        "BUNDLE_ID",
        "SIGNING_IDENTITY",
        "ASC_KEY_ID",
        "ASC_ISSUER_ID",
        "ASC_KEY_PATH",
    }
    return required.issubset({key for key, value in payload.items() if value})


def _validate_signing_config(payload: dict[str, str], source_path: Path) -> ReleaseSigningConfig:
    required_keys = [
        "TEAM_ID",
        "BUNDLE_ID",
        "SIGNING_IDENTITY",
        "ASC_KEY_ID",
        "ASC_ISSUER_ID",
        "ASC_KEY_PATH",
    ]
    missing = [key for key in required_keys if not payload.get(key)]
    if missing:
        raise RuntimeError(f"missing signing settings in {source_path}: {', '.join(missing)}")
    asc_key_path = Path(payload["ASC_KEY_PATH"]).expanduser().resolve()
    if not asc_key_path.exists():
        raise RuntimeError(f"ASC_KEY_PATH does not exist: {asc_key_path}")
    p12_raw = payload.get("P12_PATH")
    p12_path = Path(p12_raw).expanduser().resolve() if p12_raw else None
    if p12_path is not None and not p12_path.exists():
        raise RuntimeError(f"P12_PATH does not exist: {p12_path}")
    p12_password = payload.get("P12_PASSWORD")
    if p12_path is not None and not p12_password:
        raise RuntimeError("P12_PASSWORD is required when P12_PATH is provided")
    return ReleaseSigningConfig(
        team_id=payload["TEAM_ID"],
        bundle_id=payload["BUNDLE_ID"],
        signing_identity=payload["SIGNING_IDENTITY"],
        asc_key_id=payload["ASC_KEY_ID"],
        asc_issuer_id=payload["ASC_ISSUER_ID"],
        asc_key_path=asc_key_path,
        p12_path=p12_path,
        p12_password=p12_password,
    )


def _prepare_signing_keychain(signing_config: ReleaseSigningConfig) -> KeychainSession | None:
    if _identity_exists(signing_config.signing_identity, keychain_path=None):
        return None
    if signing_config.p12_path is None or signing_config.p12_password is None:
        raise RuntimeError(
            "signing identity is not available in the current keychains and no P12 credentials were provided"
        )
    temp_dir = Path(tempfile.mkdtemp(prefix="munk-signing-keychain-"))
    keychain_path = temp_dir / "munk-signing.keychain-db"
    keychain_password = secrets.token_urlsafe(24)
    _run_subprocess(
        ["security", "create-keychain", "-p", keychain_password, str(keychain_path)],
        cwd=ROOT_DIR,
    )
    _run_subprocess(
        ["security", "set-keychain-settings", "-lut", "21600", str(keychain_path)],
        cwd=ROOT_DIR,
    )
    _run_subprocess(
        ["security", "unlock-keychain", "-p", keychain_password, str(keychain_path)],
        cwd=ROOT_DIR,
    )
    _run_subprocess(
        [
            "security",
            "import",
            str(signing_config.p12_path),
            "-k",
            str(keychain_path),
            "-P",
            signing_config.p12_password,
            "-T",
            "/usr/bin/codesign",
            "-T",
            "/usr/bin/security",
        ],
        cwd=ROOT_DIR,
    )
    _run_subprocess(
        [
            "security",
            "set-key-partition-list",
            "-S",
            "apple-tool:,apple:,codesign:",
            "-s",
            "-k",
            keychain_password,
            str(keychain_path),
        ],
        cwd=ROOT_DIR,
    )
    if not _identity_exists(signing_config.signing_identity, keychain_path=keychain_path):
        raise RuntimeError(f"imported keychain does not expose signing identity: {signing_config.signing_identity}")
    return KeychainSession(path=keychain_path, password=keychain_password, temp_dir=temp_dir)


def _cleanup_signing_keychain(session: KeychainSession) -> None:
    try:
        _run_subprocess(["security", "delete-keychain", str(session.path)], cwd=ROOT_DIR, check=False)
    finally:
        shutil.rmtree(session.temp_dir, ignore_errors=True)


def _identity_exists(signing_identity: str, *, keychain_path: Path | None) -> bool:
    command = ["security", "find-identity", "-v", "-p", "codesigning"]
    if keychain_path is not None:
        command.append(str(keychain_path))
    completed = _run_subprocess(command, cwd=ROOT_DIR, capture_output=True, check=False)
    output = f"{completed.stdout}\n{completed.stderr}"
    return signing_identity in output


def _iter_signable_macho_paths(runtime_root: Path) -> list[Path]:
    signable_paths: list[Path] = []
    for candidate in runtime_root.rglob("*"):
        if not candidate.is_file() or candidate.is_symlink():
            continue
        if _is_macho_file(candidate):
            signable_paths.append(candidate)
    return _sort_signing_targets(signable_paths)


def _sort_signing_targets(paths: list[Path]) -> list[Path]:
    return sorted(
        paths,
        key=lambda path: (0 if path.suffix in {".so", ".dylib"} else 1, -len(path.parts), str(path)),
    )


def _is_macho_file(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            header = handle.read(4)
    except OSError:
        return False
    return header in MACHO_MAGIC_NUMBERS


def _codesign_runtime(
    *,
    runtime_root: Path,
    signing_config: ReleaseSigningConfig,
    keychain_path: Path | None,
) -> list[Path]:
    signed_targets: list[Path] = []
    for target_path in _iter_signable_macho_paths(runtime_root):
        _codesign_path(
            runtime_root=runtime_root,
            target_path=target_path,
            signing_config=signing_config,
            keychain_path=keychain_path,
        )
        signed_targets.append(target_path)
    return signed_targets


def _codesign_path(
    *,
    runtime_root: Path,
    target_path: Path,
    signing_config: ReleaseSigningConfig,
    keychain_path: Path | None,
) -> None:
    _run_subprocess(
        _build_codesign_command(
            runtime_root=runtime_root,
            target_path=target_path,
            signing_config=signing_config,
            keychain_path=keychain_path,
        ),
        cwd=ROOT_DIR,
    )


def _build_codesign_command(
    *,
    runtime_root: Path,
    target_path: Path,
    signing_config: ReleaseSigningConfig,
    keychain_path: Path | None,
) -> list[str]:
    uses_node_jit_entitlements = _requires_node_jit_entitlements(runtime_root=runtime_root, target_path=target_path)
    command = [
        "codesign",
        "--force",
        "--sign",
        signing_config.signing_identity,
        "--timestamp",
        "--options",
        "runtime",
        "--identifier",
        _signing_identifier_for_path(
            runtime_root=runtime_root,
            target_path=target_path,
            bundle_id=signing_config.bundle_id,
        ),
    ]
    if uses_node_jit_entitlements:
        command.extend(["--entitlements", str(NODE_JIT_ENTITLEMENTS_PATH)])
    if keychain_path is not None:
        command.extend(["--keychain", str(keychain_path)])
    command.append(str(target_path))
    return command


def _requires_node_jit_entitlements(*, runtime_root: Path, target_path: Path) -> bool:
    relative = target_path.relative_to(runtime_root)
    if relative.as_posix() == "sidecars/node/bin/node":
        return True
    return relative.parts[-4:] == ("site-packages", "playwright", "driver", "node")


def _signing_identifier_for_path(*, runtime_root: Path, target_path: Path, bundle_id: str) -> str:
    relative = target_path.relative_to(runtime_root)
    sanitized_parts = [_sanitize_identifier_part(part) for part in relative.parts]
    suffix = ".".join(part for part in sanitized_parts if part)
    return bundle_id if not suffix else f"{bundle_id}.{suffix}"


def _sanitize_identifier_part(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9.-]+", "-", value).strip(".-")


def _verify_codesign(signed_targets: list[Path]) -> None:
    for target_path in signed_targets:
        _run_subprocess(
            ["codesign", "--verify", "--strict", "--verbose=2", str(target_path)],
            cwd=ROOT_DIR,
        )


def _verify_notarized_targets(paths: list[Path]) -> None:
    seen_paths: set[Path] = set()
    for path in paths:
        target_path = path.resolve()
        if target_path in seen_paths:
            continue
        seen_paths.add(target_path)
        _run_subprocess(
            ["codesign", "--verify", "--strict", "--check-notarization", "--verbose=2", str(target_path)],
            cwd=ROOT_DIR,
        )


def _notarize_archive(*, archive_path: Path, signing_config: ReleaseSigningConfig) -> NotarizationResult:
    command = _build_notarytool_command(archive_path=archive_path, signing_config=signing_config)
    completed = _run_subprocess(
        command,
        cwd=ROOT_DIR,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "notarytool submit failed.\n"
            f"archive: {archive_path}\n"
            f"{_format_subprocess_failure(command=command, cwd=ROOT_DIR, returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)}"
        )
    payload = json.loads(completed.stdout)
    status = str(payload.get("status", "")).strip()
    submission_id = str(payload.get("id", "")).strip()
    if not status:
        raise RuntimeError(f"notarytool returned an unexpected payload: {payload}")
    if status.lower() != "accepted":
        raise RuntimeError(f"notarization failed with status={status}, submission_id={submission_id or 'unknown'}")
    return NotarizationResult(
        submission_id=submission_id,
        status=status,
        message=str(payload.get("message", "")),
        raw_payload=payload,
    )


def _build_notarytool_command(*, archive_path: Path, signing_config: ReleaseSigningConfig) -> list[str]:
    return [
        "xcrun",
        "notarytool",
        "submit",
        str(archive_path),
        "--key",
        str(signing_config.asc_key_path),
        "--key-id",
        signing_config.asc_key_id,
        "--issuer",
        signing_config.asc_issuer_id,
        "--wait",
        "--output-format",
        "json",
    ]


def _run_subprocess(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    capture_output: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(  # noqa: S603
            command,
            cwd=cwd,
            env=env,
            check=check,
            capture_output=capture_output,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            _format_subprocess_failure(
                command=list(exc.cmd) if isinstance(exc.cmd, (list, tuple)) else [str(exc.cmd)],
                cwd=cwd,
                returncode=exc.returncode,
                stdout=exc.stdout,
                stderr=exc.stderr,
            )
        ) from exc


def _format_subprocess_failure(
    *,
    command: list[str],
    cwd: Path,
    returncode: int,
    stdout: str | None,
    stderr: str | None,
) -> str:
    parts = [
        f"command failed with exit code {returncode}",
        f"cwd: {cwd}",
        f"command: {' '.join(command)}",
    ]
    stdout_text = (stdout or "").strip()
    stderr_text = (stderr or "").strip()
    if stdout_text:
        parts.append(f"stdout:\n{stdout_text}")
    if stderr_text:
        parts.append(f"stderr:\n{stderr_text}")
    return "\n".join(parts)
