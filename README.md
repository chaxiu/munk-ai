# Munk AI

> AI testing infrastructure for Harness Engineering across Android, iOS, and Web.

Munk AI is local-first AI testing for the AI era.

It brings visual understanding, structured planning, and real-device execution into one validation loop.
Built to give Harness Engineering a real-world feedback loop.

Not another XPath-driven test framework.
Built to turn natural-language intent into product-level validation.

## Demo

![Trae + Munk AI demo](./assets/output-4fps.gif)

*Trae + Munk AI adds a delete feature to a Todo app, compiles the build, and runs automated validation on Android.*

## Why Munk AI

Code generation is no longer the bottleneck.
Verification is.

Most AI workflows still depend on humans to compile builds, click through UIs, inspect failures, take screenshots, and translate bugs back into prompts.

Munk AI closes that loop.
It tests the product itself, not just code, mocks, or static analysis.

- Visual-first validation over fragile selectors and manual click-through testing
- Real Android, iOS, and Web execution instead of mocked or partial feedback
- Structured evidence out: screenshots, UI trees, runtime logs
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

### The New Loop: Agent Orchestration for Harness Engineering

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

## Architecture

Munk AI exposes one validation engine through multiple entry points:

- CLI for local developer workflows
- MCP for coding agents and automation systems
- Local Web UI for recording, asset management, and batch execution
- Local API for integration with surrounding tools

This design allows the same core engine to serve developers, QA, CI workflows, and AI agents without maintaining separate business logic for each surface.

## Current Status

Munk AI is under active development.

- Public repo is live; core modules will be opened in stages.
- App Knowledge support is complete.

## Roadmap

- [x] App Knowledge support
- [x] Polished CLI workflows
- [x] Stable MCP support for coding agents
- [x] Local Web UI for recording, planning, and execution
- [x] macOS release
- [ ] Core modules open source
- [ ] Windows support
- [ ] Linux support

## Vision

Code gets cheaper.
Verification gets more important.

Munk AI is built for that shift.
The goal is simple: give AI-generated software a real feedback loop.
That is how Harness Engineering becomes practical.

## Contact

- Twitter / X: [@iBoyCoder](https://x.com/iBoyCoder)
- WeChat Official Account: `@朱涛的自习室`

## License

AGPL-3.0. See [License.txt](./License.txt).
