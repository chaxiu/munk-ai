# review-runtime-local

`review-runtime-local` 是 `ai-monkey` 当前默认的本地 review runtime 实现包。

它依赖 `review-agent-api` 定义的 contract，对外通过 entry point 注册为 `munk.review.runtimes` 下的 `local` runtime。

## 定位

- 实现 review runtime 协议
- 持有本地 review 知识库和检索实现
- 持有 prompt 组装、模型调用、结果物化逻辑
- 生成 review 对外交付产物
  - `review_result.json`
  - `review_orchestration.json`
  - `artifact_manifest.json`
  - `diagnostics.json`

它是“具体实现层”，不是 contract 层。

## 与主仓和 review-agent-api 的关系

- `review-runtime-local` 依赖 `review-agent-api`
  - 输入输出模型、schema、runtime protocol 都来自 `review-agent-api`
- 主仓不应直接依赖这里的内部模块
  - 主仓应通过 `review-agent-api` 的 runtime 协议发现并调用 runtime
- 主仓只消费这里产出的公开 contract 文件
  - 例如 `review_result.json`
  - 例如 `review_orchestration.json`

关系可以概括为：

- 主仓：通过 `review-agent-api` 调 runtime，并消费公开产物
- `review-agent-api`：定义 runtime protocol 和共享 schema
- `review-runtime-local`：负责实际执行 review 并写出产物

## 当前职责边界

这里适合放：

- 知识库目录与构建逻辑
- 检索实现
- 本地模型配置与模型构建
- prompt 组装
- `ReviewResult` 生成
- `ReviewOrchestrationContract` 生成
- runtime 内部的 artifact/diagnostics 写出逻辑

这里不适合放：

- 主仓 planner / runner / execution 内部逻辑
- 主仓 service 层工具实现
- 主仓内部 DTO
- 需要被多个 runtime 共享的公开 contract

如果某个类型或 schema 需要被主仓和多个 runtime 共享，应优先放回 `review-agent-api`。

## 对外产物与内部产物

### 对外公开 contract 产物

这些文件会被主仓读取或透出，应保持稳定：

- `review_result.json`
- `review_orchestration.json`
- `artifact_manifest.json`
- `diagnostics.json`

这些文件的字段语义和 schema 受 `review-agent-api` 定义约束。

### runtime 内部产物

这些文件可以作为实现细节演进，但主仓不应依赖：

- 检索调试信息
- 中间缓存
- prompt trace
- 本地构建目录下的私有索引文件
- 任何只服务于 runtime 内部调试或性能优化的文件

原则是：可以改变内部实现，但不要破坏主仓可见 contract。

## 维护原则

- 可以持续优化实现，但不要把主仓依赖重新拉回来
- 不要直接依赖主仓 `services`、`paths`、`planning` 等实现层模块
- 与主仓共享的 DTO / schema 不要在这里复制定义
  - 应复用 `review-agent-api`
- 如果需要主仓内部模型，应该让主仓自己做 adapter
  - runtime 不应直接知道主仓内部执行模型
- 产物文件名、schema version、必填字段变更时，要同步评估主仓兼容性

## 后续扩展建议

如果未来新增其他 review runtime：

- 复用 `review-agent-api` 的 runtime protocol 和 contract
- 保持主仓调用链不变
- 各 runtime 可以有不同内部实现，但对外产物 contract 应保持兼容

这样主仓才能继续只依赖 `review-agent-api`，而不是依赖具体 runtime。
