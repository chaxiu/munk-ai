# review-agent-api

`review-agent-api` 是 `ai-monkey` review 能力的共享 contract 包。

它的职责不是执行 review，也不是持有知识库或模型实现；它的职责是定义主仓和 review runtime 之间共享的边界。

## 定位

- 为主仓提供稳定的 review 请求/响应 DTO
- 为 review runtime 提供稳定的 runtime protocol
- 为主仓和 runtime 提供共享的 orchestration contract schema
- 作为独立分发边界，避免主仓直接依赖某个具体 runtime 实现

当前主仓通过 `review-agent-api` 暴露的 runtime 协议发现并调用已安装的 review runtime，具体入口见：

- `munk.reviewing.runtime`
- `munk.reviewing.models`
- `munk.reviewing.orchestration_models`

## 与主仓和 runtime 的关系

- 主仓依赖 `review-agent-api`
  - 主仓只应消费这里定义的 DTO、schema 和 runtime protocol
  - 主仓不应直接 import `review-runtime-local` 内部模块
- `review-runtime-local` 依赖 `review-agent-api`
  - runtime 负责生成符合这些 contract 的产物
  - runtime 可以有自己的内部实现和中间文件，但不能破坏这里定义的外部 schema

关系可以概括为：

- 主仓：消费 contract
- `review-agent-api`：定义 contract
- `review-runtime-local`：实现 contract

## 当前包含的边界

- review 请求/结果模型
  - `ReviewRequest`
  - `ReviewResult`
  - `ReviewFinding`
  - `SuggestedFollowUpCase`
- review runtime 协议
  - `ReviewRuntime`
  - `ReviewRuntimeFactory`
  - runtime entry point discovery
- review orchestration contract
  - `ReviewOrchestrationContract`
  - `ReviewRequiredCase`
  - `ReviewAdvisoryCase`
  - `ReviewHintBlock`

## 明确不放什么

`review-agent-api` 不应该承载以下内容：

- 主仓内部业务模型
  - 例如 `TestCase`、planner 内部模型、runner 内部模型
- 具体 runtime 实现
  - 例如知识库检索、prompt 组装、模型调用、artifact 落盘
- provider-specific 逻辑
  - 例如 local runtime 的资源路径、embedding 模型、sqlite 构建细节
- 业务编排实现
  - 例如如何从 `ReviewResult` 组装 `review_orchestration.json`

## 维护原则

- 优先保持 contract 稳定
  - schema 变更会同时影响主仓和 runtime
- 新增字段优先向后兼容
  - 尽量新增 optional 字段，而不是破坏已有字段语义
- 不要把主仓内部模型泄漏到这里
  - 主仓内部模型应在主仓侧做 adapter 转换
- 不要把 runtime 内部实现拉进这里
  - `review-agent-api` 只负责“长什么样”，不负责“怎么做出来”

## 变更 checklist

修改 `review-agent-api` 前，至少确认：

- 这个类型是否真的是跨边界共享的 contract
- 这个改动是否会影响主仓读取已有 review 产物
- 这个改动是否会影响 runtime 写出已有 review 产物
- 是否需要提升 schema version 或增加兼容逻辑

如果答案更偏向“主仓内部使用”或“runtime 内部实现”，那通常不应该放在这里。
