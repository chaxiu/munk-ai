# Scripts

`scripts/` contains repository-local helper scripts.

## Placement Rules

- Keep root-level scripts only for top-level build, bootstrap, publish, or cross-domain entrypoints.
- Move domain-specific helper scripts into subdirectories instead of continuing to grow the root.
- Prefer moving shared logic into `src/` packages when it becomes part of the product/runtime contract, rather than building large script-to-script dependency chains.

## Root-Level Scripts

These scripts remain at `scripts/` root because they are primary entrypoints or cross-domain helpers:

- `assemble_standalone_runtime.py`: assemble the release runtime
- `bootstrap_standalone_dev.py`: bootstrap the dev runtime
- `publish_release_artifacts.py`: publish release artifacts
- `update_uv_locks.py`: refresh workspace locks
- `verify_standalone_runtime.py`: verify assembled runtime
- `build_review_knowledge.py`: build review knowledge assets
- `generate_local_api_openapi.py`: generate/check Local API OpenAPI output
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
python3 scripts/device/install_simulator_wda.py --simulator-udid <udid>
python3 scripts/device/check_ios_wda_signing.py --signing-env-file /path/to/ios.env
python3 scripts/perception/export_icon_detect_onnx.py
```

## Rule Of Thumb

- If a script is something a developer is likely to run as a main workflow entry, keep it easy to discover at root.
- If a script is tied to one technical area, put it under that area.
- If a script starts accumulating reusable business logic, move that logic into `src/` and keep the script thin.
