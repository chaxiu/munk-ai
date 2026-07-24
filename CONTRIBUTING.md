# Contributing To Munk

Thanks for contributing to Munk.

This repository is organized as a host application plus contract packages and runtime implementations. The best contributions usually strengthen one of those boundaries instead of adding ad hoc logic across several layers at once.

## Before You Start

- Use Python 3.10 or newer
- Use Node.js 20 or newer
- Use `pnpm` for workspace JavaScript packages
- Use `uv` for Python dependency and test workflows

The primary local command entry point is:

```bash
munk
```

## Repository Structure

The main repository areas are:

- `src/munk/`: host application, entry adapters, orchestration, and artifact handling
- `packages/agents/*`: agent contracts and runtime implementations
- `packages/devices/*`: device contracts and platform runtimes
- `packages/shared/*`: shared contracts, perception packages, and cross-agent foundations
- `apps/*`: user-facing applications such as the local web UI
- `sidecars/*`: companion local processes such as recording bridges
- `tests/`: host-level tests and integration coverage
- `examples/`: sample configuration files
- `scripts/`: bootstrap, packaging, and maintenance scripts

Repository structure is intentional:
new independently owned modules should generally live under `packages/`, `apps/`, or `sidecars/` rather than as new root-level projects.

If you are deciding where a change belongs, prefer these rules:

- put cross-boundary DTOs and protocols in the relevant `*-api` package
- put concrete execution behavior in the matching runtime package
- put user-facing applications in `apps/*` and companion local processes in `sidecars/*`
- keep CLI, Local API, and MCP adapters thin
- avoid introducing new root-level feature directories when an existing package domain already fits

## Development Setup

Update locks and bootstrap the development runtime:

```bash
python3 scripts/update_uv_locks.py
python3 scripts/bootstrap_standalone_dev.py --force
./dist/runtime-dev/bin/munk doctor
```

This is the recommended development path because it assembles the project in the same runtime shape used for local validation.

## Common Commands

### Python tests

Run the full Python test suite:

```bash
uv run --project . --extra test pytest
```

Run workspace-oriented tests:

```bash
bash scripts/run_workspace_tests.sh
```

### Lint and type checks

```bash
uv run --project . --extra lint ruff check .
uv run --project . --extra lint ruff format --check .
uv run --project . --extra lint pyright
```

### Frontend workspace commands

Install JavaScript dependencies:

```bash
pnpm install
```

Build all workspace packages:

```bash
pnpm -r build
```

Run the local web UI in development mode:

```bash
pnpm --dir apps/web-ui dev
```

Run frontend checks:

```bash
pnpm --dir apps/web-ui type-check
pnpm --dir apps/web-ui test -- --run
pnpm --dir apps/web-ui lint
```

### Contract generation

Regenerate local API and frontend contracts:

```bash
pnpm run generate:contracts
```

Check whether generated contracts are up to date:

```bash
pnpm run check:contracts
```

## Contribution Guidelines

### 1. Prefer clear boundaries

This repository intentionally separates:

- entry adapters
- orchestration host logic
- stable contracts
- runtime implementations

When making a change, keep that separation intact whenever possible.

### 2. Treat contract packages carefully

Changes to `*-api/`, `shared-api/`, or `shared-tools-api/` affect multiple packages.

Before changing a contract:

- confirm the type is truly shared across boundaries
- prefer backward-compatible additions
- avoid moving host-only or runtime-private details into contract packages

### 3. Keep public surfaces stable

The most important public-facing surfaces are:

- the `munk` CLI
- the Local API
- MCP endpoints
- the human-facing local web UI for QA-oriented device management, test asset management, and batch execution

Changes that affect these areas should come with clear validation and, when appropriate, documentation updates.

### 4. Keep implementation details implementation details

Not every internal directory is a public extension surface.

Avoid documenting or depending on internal behavior such as:

- prompt assembly internals
- runtime-private storage details
- bridge-private session behavior
- provider-specific resource layouts

### 5. Update docs when behavior changes

If your change affects public behavior, update:

- `README.md`
- `docs/public/architecture.md`
- this contributing guide when the workflow for contributors changes

## Testing Expectations

Choose the smallest set of checks that gives confidence for your change.

Typical examples:

- contract changes: update relevant package tests
- host orchestration changes: run targeted service or adapter tests
- frontend changes: run `web-ui` type checks and tests
- end-to-end behavior changes: run focused smoke or runtime-dev validation where practical

If a change affects multiple layers, mention what you ran in your handoff or pull request description.

## Documentation Style

For public-facing documentation in this repository:

- write in English
- prefer concise, high-signal explanations
- describe stable architecture and supported workflows
- avoid exposing internal implementation details as if they were public contracts

## Pull Request Notes

When opening a pull request, it helps to include:

- what changed
- why the change belongs in the chosen layer
- what commands or tests you ran
- any public documentation updates

## Questions

If you are unsure where a change should live, start from the contract and ownership boundaries rather than from the nearest existing file.

That usually leads to cleaner contributions and fewer accidental architecture leaks.
