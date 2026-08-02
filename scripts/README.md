# Scripts

`scripts/` contains repository-local helper scripts.

## Placement Rules

- Keep root-level scripts only for top-level build, bootstrap, publish, or cross-domain entrypoints.
- Move domain-specific helper scripts into subdirectories instead of continuing to grow the root.
- Prefer moving shared logic into `src/` packages when it becomes part of the product/runtime contract, rather than building large script-to-script dependency chains.

## Root-Level Scripts

These scripts remain at `scripts/` root because they are primary entrypoints or cross-domain helpers:

- `assemble_standalone_runtime.py`: assemble the release runtime; generates Local API OpenAPI and frontend contracts before build assembly
- `bootstrap_standalone_dev.py`: bootstrap the dev runtime; generates Local API OpenAPI and frontend contracts before runtime bootstrap
- `publish_release_artifacts.py`: publish release artifacts
- `sync_public_repo.sh`: sync the public-repo allowlist into `public/munk-ai`
  - Reuses root `.gitignore` for local noise / large resources
  - Policy denylist for private paths (explicitly includes top-level `cloud/`)
  - Protects destination `.github/` (public-repo-owned Release CI; never overwritten)
  - Allowlist: build manifests + `apps` / `assets` / `packages` / `scripts` / `sidecars` / `src`
  - Default `--delete` preserves destination `.git`; pass `--delete-excluded` to also clean excluded junk
- `ci/`: helpers used by the public-repo GitHub Actions release workflow
  - examples: `materialize_macos_signing.sh`, `materialize_r2_publish_env.sh`
- `update_uv_locks.py`: refresh workspace locks
- `verify_standalone_runtime.py`: verify assembled runtime
- `build_review_knowledge.py`: build review knowledge assets
- `generate_local_api_openapi.py`: generate/check Local API OpenAPI output
- `generate_loop_local_api_openapi.py`: generate/check trimmed Local API OpenAPI for Munk Loop (`munk-loop/docs/munk-ai/local-api.loop.json`)
- `install.sh`: installer entrypoint

## Subdirectories

- `device/`: device environment setup and WDA / Android tooling helpers
  - examples: `install_simulator_wda.py`, `install_real_device_wda.py`, `download_android_platform_tools.py`
- `branding/`: brand and visual asset helpers
  - examples: `generate_logo_assets.py`, `generate_website_social_cards.py`
- `perception/`: perception model export and local verification helpers
  - examples: `export_icon_detect_onnx.py`, `build_perception_wheels.sh`

## Quick Examples

```bash
python3 scripts/bootstrap_standalone_dev.py --force
python3 scripts/assemble_standalone_runtime.py --force
./scripts/sync_public_repo.sh --dry-run
python3 scripts/device/install_simulator_wda.py --simulator-udid <udid>
python3 scripts/device/check_ios_wda_signing.py --signing-env-file /path/to/ios.env
python3 scripts/perception/export_icon_detect_onnx.py
```

## iOS Notes

- 当前正式 iOS runtime 边界：
  - simulator discovery / bootstrap：本地 `simctl` + simulator WDA
  - real-device discovery / session：`ios-device-bridge`
  - iOS 18+ tunnel：sudo 启动的 `ios-device-bridge`
- `scripts/device/install_real_device_wda.py`、`scripts/device/install_wda.py`、`scripts/device/check_ios_wda_signing.py`
  - 当前定位是 **legacy/manual helper**
  - 用途是独立准备或排查真机 WDA 安装/签名环境
  - 它们**不是**当前 Munk 真机 discovery / session 的正式主链
- 新的真机主链应优先从：
  - `./dist/runtime-dev/bin/munk serve`
  - Local API `/v1/devices?platform=ios`
  - `ios-device-bridge`
  进入，而不是先从旧脚本 transport 心智出发

## Rule Of Thumb

- If a script is something a developer is likely to run as a main workflow entry, keep it easy to discover at root.
- If a script is tied to one technical area, put it under that area.
- If a script starts accumulating reusable business logic, move that logic into `src/` and keep the script thin.
