# Munk AI

Local-first, self-improving AI testing engine across Android, iOS, and Web.

It brings visual understanding, structured planning, real-device execution, and knowledge accumulation into one validation loop.
Built to give teams and coding agents a feedback loop that improves over time.

Not another XPath-driven test framework.
Built to turn natural-language intent into product-level validation.

## Demo

![Trae + Munk AI demo](./assets/output-4fps.gif)

*From feature request to real-device validation: Trae + Munk AI implements a new delete flow, builds the project, and verifies the change automatically.*

## Get Started

Available on macOS today.

Install Munk AI, run diagnostics, and start the local Web UI:

```bash
curl -fsSL https://get.munk.sh | sh
munk doctor
munk serve --port 16888
```

For docs and updates, visit [munk.sh](https://www.munk.sh/).

## Build Locally

To prepare the local `runtime-dev` environment from source:

```bash
python3 scripts/update_uv_locks.py
python3 scripts/bootstrap_standalone_dev.py --force
./dist/runtime-dev/bin/munk doctor
./dist/runtime-dev/bin/munk serve --port 16888
```

## Why Munk AI

Code generation is no longer the bottleneck.
Verification is.

Most AI workflows still depend on humans to compile builds, click through UIs, inspect failures, take screenshots, and translate bugs back into prompts.

Munk AI closes that loop.
It tests the product itself, not just code, mocks, or static analysis.

- Visual-first validation over fragile selectors and manual click-through testing
- Real Android, iOS, and Web execution instead of mocked or partial feedback
- Structured evidence out: screenshots, UI trees, runtime logs
- Self-improving loop: execution evidence becomes better knowledge and guidance
- Local-first by default: lower cost, tighter privacy, more control
- One engine for developers, QA teams, and coding agents

### The Old Loop: Humans As Test Operators

```mermaid
graph TD
    classDef human fill:#E8F0FE,stroke:#1A73E8,stroke-width:2px,color:#1A73E8;
    classDef codingAgent fill:#FCE8E6,stroke:#D93025,stroke-width:2px,color:#D93025;
    classDef manualTest fill:#FEF7E0,stroke:#F29900,stroke-width:2px,color:#B06000,stroke-dasharray: 5 5;

    H1(👤 Human<br/>Defines the requirement):::human
    A1(🤖 Coding Agent<br/>Generates the code):::codingAgent
    H2(👀 Human tester<br/>Compiles, clicks, checks errors):::manualTest
    H3(📸 Human feedback loop<br/>Screenshots and writes context):::manualTest

    H1 -->|Instruction| A1
    A1 -->|Build and run| H2
    H2 -->|Bug found| H3
    H3 -->|Feed context back| A1
    H2 -->|If it looks correct| END((Delivery))

    subgraph Open-loop vibe coding
        H1
        A1
    end

    subgraph Human-as-feedback bottleneck
        H2
        H3
    end
```

### The New Loop: Agent Orchestration for Product Validation

```mermaid
graph TD
    classDef human fill:#E8F0FE,stroke:#1A73E8,stroke-width:2px,color:#1A73E8;
    classDef codingAgent fill:#FCE8E6,stroke:#D93025,stroke-width:2px,color:#D93025;
    classDef testAgent fill:#E6F4EA,stroke:#137333,stroke-width:2px,color:#137333;
    classDef coreEngine fill:#CEEAD6,stroke:#0D652D,stroke-width:3px,color:#0D652D,stroke-dasharray: 5 5;
    classDef device fill:#FFF3E0,stroke:#E65100,stroke-width:2px,color:#E65100,stroke-dasharray: 5 5;

    H1(👤 Human<br/>Defines goals and acceptance criteria):::human
    A1(🤖 Coding Agent<br/>Writes the code):::codingAgent
    D1(📱 Device / Emulator / Browser<br/>Real execution environment):::device
    M1(👁️ Munk AI<br/>Testing agent):::testAgent
    C1(📝 Structured bug context<br/>Screenshots, UI tree, logs):::testAgent

    H1 -->|Goals and constraints| A1
    A1 -->|Deploy build| D1
    A1 -->|Trigger validation| M1
    M1 -->|Tap, type, verify| D1
    D1 -.->|Live UI feedback| M1
    M1 -->|Validation failed| C1
    C1 -->|Self-healing feedback| A1
    M1 -->|Validation passed| H1

    subgraph Agent orchestration closed loop
        A1
        D1
        M1
        C1
    end

    class M1 coreEngine;
```

## What It Does

Plan. Run. Review. Verify.

- Turn natural-language requirements into structured test plans
- Run cross-platform validation on Android, iOS, and Web
- Record interactions and turn them into reusable test assets
- Review code changes and infer regression scope automatically
- Return real UI evidence back into agent workflows

## Why It Self-Improves

Munk AI is built as a self-improving testing engine.

When a run fails, retries, or gets stuck, it learns from execution evidence.
It turns failures into knowledge candidates and optimization hints for future runs.
That makes planning, review, and validation more accurate over time.

## Architecture

Munk AI exposes one validation engine through multiple entry points:

- CLI for local developer workflows
- MCP for coding agents and automation systems
- Local Web UI for QA-oriented device management, test asset management, and batch execution
- Local API for integration with surrounding tools

This design allows the same core engine to serve developers, QA, CI workflows, and AI agents without maintaining separate business logic for each surface.
It also includes a self-improving post-action loop, where optimization and knowledge agents feed better context into future runs.

```mermaid
flowchart TD
    classDef entry fill:#E8F0FE,stroke:#1A73E8,stroke-width:2px,color:#1A73E8;
    classDef host fill:#FCE8E6,stroke:#D93025,stroke-width:2px,color:#D93025;
    classDef workflow fill:#E6F4EA,stroke:#137333,stroke-width:2px,color:#137333;
    classDef infra fill:#FFF3E0,stroke:#E65100,stroke-width:2px,color:#E65100,stroke-dasharray: 5 5;
    classDef platform fill:#F3E8FD,stroke:#9334E6,stroke-width:2px,color:#6A1B9A,stroke-dasharray: 5 5;

    A(🧰 CLI<br/>Local command entry):::entry
    B(🔌 Local API<br/>Programmatic control surface):::entry
    C(🧩 MCP<br/>External tool integration):::entry
    D(🖥️ QA Web UI<br/>Human-facing workspace):::entry

    E(🎛️ Orchestration Host<br/>Coordinates runs and artifacts):::host

    P(📝 Plan<br/>Task planning):::workflow
    R(🏃 Runner<br/>Execution loop):::workflow
    J(⚖️ Judge<br/>Outcome evaluation):::workflow
    X(🛠️ Optimize Agent<br/>Post-run guidance optimization):::workflow
    K(🧠 Knowledge Agent<br/>Execution-driven knowledge distillation):::workflow
    V(🔍 Review<br/>Result inspection):::workflow
    O(📼 Recording<br/>Capture and replay flow):::workflow

    DP(📱 Device and Perception<br/>Execution and sensing layer):::infra
    L(🔗 Local Bridge<br/>Recording transport):::infra

    AX(🤖 Android<br/>Runtime target):::platform
    WX(🌐 Web<br/>Runtime target):::platform
    IX(🍎 iOS<br/>Evolving runtime target):::platform

    A --> E
    B --> E
    C --> E
    D --> B

    E --> P
    E --> R
    E --> J
    E --> X
    E --> K
    E --> V
    E --> O

    R --> DP
    J --> X
    J --> K
    X -. Better guidance .-> P
    K -. Better knowledge .-> P
    K -. Better context .-> V
    O --> L

    DP --> AX
    DP --> WX
    DP --> IX

    subgraph Entry surfaces
        A
        B
        C
        D
    end

    subgraph Core orchestration
        E
        P
        R
        J
        X
        K
        V
        O
    end

    subgraph Runtime and platform layer
        DP
        L
        AX
        WX
        IX
    end
```

Repository-level architecture follows a layered, package-oriented model:

- `src/munk/` hosts the main entry surfaces, orchestration, adapters, and artifact handling
- `packages/agents/*` contains agent-facing contract packages and local runtime implementations
- `packages/devices/*` contains cross-platform device contracts and platform-specific runtimes
- `packages/shared/*` contains shared contracts, perception packages, and cross-agent foundations
- `apps/web-ui/` and `sidecars/recording-bridge-local/` support the human-facing QA UI and local recording flow

Repository structure reflects ownership boundaries as well as layering:
independently owned or distributed units live under `packages/`, `apps/`, or `sidecars/` rather than as scattered root-level projects

Platform support should be read as workflow maturity rather than repository presence alone:

- Android is the primary local execution path today
- Web support is available and evolving
- iOS support exists in the repository and continues to evolve

For a public overview, see [docs/public/architecture.md](./docs/public/architecture.md).
For contributor setup and repository guidance, see [CONTRIBUTING.md](./CONTRIBUTING.md).

## Current Status

Munk AI is under active development.

- Open source and evolving in public.
- App Knowledge support is complete.
- Self-improving execution loop is part of the core product direction.

## Roadmap

- [x] App Knowledge support
- [x] Polished CLI workflows
- [x] Stable MCP support for coding agents
- [x] Local Web UI for device management, test asset management, and batch execution
- [x] macOS release
- [x] Public open-source release
- [ ] CI & Release Setup
- [ ] Docs and CONTRIBUTING guide
- [ ] Windows support
- [ ] Linux support
- [ ] iOS environment setup
- [ ] Web environment setup
- [ ] Advanced agent


## Tech Stack

### Core Runtime

- Python 3.10
- FastAPI
- Typer CLI
- Pydantic / PydanticAI
- NumPy / OpenCV

### Device Execution

- Android: `uiautomator2`
- Web: `Playwright + Chromium`
- iOS: dedicated runtime integration

### Local UI And Tooling

- Vue 3
- TypeScript
- Vite
- TanStack Query
- vue-i18n

### Bridge Layer

- Node.js
- Fastify
- WebSocket
- scrcpy ecosystem for local Android device streaming and control


## Vision

Code gets cheaper.
Verification gets more important.

Munk AI is built for that shift.
The goal is simple: give AI-generated software a real feedback loop.
Not only a loop that runs, but a loop that learns from evidence and improves over time.
That is how Harness Engineering becomes practical.

## Contact

- Twitter / X: [@iBoyCoder](https://x.com/iBoyCoder)
- WeChat Official Account: `@朱涛的自习室`

## License

AGPL-3.0. See [License.txt](./License.txt).
