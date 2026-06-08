# web-ui

`apps/web-ui/` 是 `munk serve` 托管的 Local Web GUI 前端包。`Phase 7N-A1` 之后，它不再只是单页 recording MVP，而是 Local Web GUI 的通用前端壳。

## 当前职责

- 承载 Local Web GUI 的 App Shell、一级导航与页面壳
- 消费 `A0` 产出的 generated contracts 与 shared typed api client
- 承载当前已完整可跑通的 `recording` feature
- 为后续 `operations / artifacts / workflows / assets / settings` 预留稳定模块位置

## 技术基线

- `Vue 3 + TypeScript + Vite`
- `vue-router`：history router，base 为 `/`
- `@tanstack/vue-query`：query / mutation / polling 基础设施
- `vue-i18n`：多语言骨架
- `openapi-fetch`：基于 `A0` generated contracts 的 typed Local API client

## 目录结构

```text
src/
  app/
    AppRoot.vue
    providers/
    router/
    shell/
  features/
    home/
    recording/
    operations/
    artifacts/
    workflows/
    assets/
    settings/
  shared/
    api/
    contracts/generated/
    components/
    i18n/
    logging/
    query/
    theme/
```

分层原则：

- `app/`：应用启动、providers、router、App Shell
- `features/`：按业务领域组织页面、模块组件、query hooks
- `shared/`：跨 feature 复用的 API、contracts、UI 原语、i18n/theme/logging/query 基础设施

## 路由与托管

- 前端 router 采用 history 模式，目标 URL 为 `/...`
- Vite 静态资源基路径保持根路径 `/`
- Local API 负责：
  - `/` 返回 SPA 入口
  - 真实静态资源路径如 `/assets/*`、`/favicon.ico` 直接返回构建产物
  - 其他前端路径 `/{path:path}` 返回同一 SPA 入口

这层后端逻辑只属于 GUI 托管层基础设施，不是业务 API 膨胀。

## 开发命令

安装依赖：

```bash
pnpm install
```

本地开发：

```bash
pnpm --dir apps/web-ui dev
```

类型检查：

```bash
pnpm --dir apps/web-ui type-check
```

单测：

```bash
pnpm --dir apps/web-ui test -- --run
```

Lint：

```bash
pnpm --dir apps/web-ui lint
```

构建：

```bash
pnpm --dir apps/web-ui build
```

## Contract 生成

生成前端 typed contracts：

```bash
pnpm --dir apps/web-ui run generate:local-api-types
```

检查 generated contract 是否最新：

```bash
pnpm --dir apps/web-ui run check:local-api-types
```

OpenAPI schema 的来源与生成方式见仓库根 [tests/README.md](file:///Users/zhutao/Cursor/ai-monkey/tests/README.md)。

## A1 验收提示

- `Phase 7N-A1` 的完成态默认基于 `history router + Local API GUI catch-all`
- 手工验证时应至少覆盖 `/`、`/operations`、`/settings` 的直达与刷新
- 若出现子路由 404，应优先排查 router base、构建产物路径和 Local API fallback，而不是回退到 `hash router`
