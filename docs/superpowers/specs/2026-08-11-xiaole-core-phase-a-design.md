# 小乐 2.0 Core Phase A 设计

## 目标与边界

Phase A 在现有 `xiaole-backend` 内新增独立、薄、可测试的 Brain Core，验证三条路径：普通对话、Brain → 乐知 Memory、Brain → 小可 Action。旧 `XiaoLeAgent`、旧 Memory、Task、Reminder、ToolRegistry、TaskExecutor、行为学习和主动系统保持原状且不接入新 Core；不修改乐知或小可，不迁移数据，不切换生产 Web，不部署，不发送真实 Bark。

长期职责固定为：小乐 = Brain，乐知 = Memory，小可 = Action。新 Core 不读取乐知文件、索引或数据库，也不理解小可的 Attempt、Dispatcher、Adapter、monitor-service 或 Bark。

## 选定方案

采用“独立 Core + 端口适配器”。`/api/v2/chat` 通过现有 `get_current_user` JWT 依赖取得当前用户，调用独立 `BrainCore`。Core 只依赖抽象的 Context Repository、Model Router、Memory Gateway 和 Action Gateway，不实例化或导入旧 `XiaoLeAgent`。

旧代码只允许复用稳定基础设施：现有 JWT 依赖、SQLAlchemy 的 `Conversation`/`Message` 模型和数据库 Session。不得复用旧 Agent 的业务方法。

## 模块结构

```text
xiaole_core/
  brain.py             单轮编排
  intent.py            conversation/memory/action 分类
  context.py           短期上下文及 conversations/messages 适配
  models.py            primary/fallback 模型路由
  persona.md           唯一运行时人格
  schemas.py           API/Core/Gateway 契约
  errors.py            领域错误
  dependencies.py      独立依赖组装
  gateways/
    memory.py           乐知 HTTP 适配
    action.py           小可 HTTP 适配
routers/chat_v2.py      JWT 保护的 POST /api/v2/chat
tests/xiaole_core/      单元、API、架构与安全测试
```

## API 与身份隔离

`POST /api/v2/chat` 必须携带现有小乐 Bearer JWT，并直接复用 `Depends(get_current_user)`。不新增认证代码、Token 格式、OAuth 或匿名入口。请求体：

```json
{"message":"你好","conversation_id":null,"attachments":[]}
```

响应体：

```json
{
  "request_id":"uuid",
  "conversation_id":"uuid",
  "intent":"conversation",
  "answer":"...",
  "sources":[],
  "action":null,
  "diagnostics":{"model":"deepseek","gateway_used":null,"latency_ms":1,"fallback":false}
}
```

`diagnostics` 是固定白名单模型，不得出现 Token、Secret、完整 Prompt 或用户隐私原文。无/非法 JWT 返回 401；访问其他用户的 conversation 返回 403；请求错误返回 400/422；领域依赖不可用以安全、诚实的 200 回答表达；未预期错误返回无内部细节的 500。

Context Repository 使用 `user_id + conversation_id` 联合校验。未传 conversation_id 时为当前用户创建会话；读取最近 12 条消息（最多 6 轮）；只写 `conversations` 和 `messages`。不得读取或写入任何旧长期 Memory、Task、Reminder、行为或主动系统表。Gateway 结果仅存在于本轮内存。

## Intent Router

Phase A 只有 `conversation`、`memory`、`action`。确定性规则优先：测试手机通知为 action，官方通知/长期知识为 memory，其余明确普通交流为 conversation。模糊输入最多调用一次模型分类 fallback；输出必须解析为枚举，非法或失败时安全回退 conversation。Router 只返回决策，不持有或调用 Gateway、Tool、Task。

## Model Router 与 Persona

模型调用只有一个薄入口，primary 使用现有 DeepSeek 配置，fallback 使用现有 Qwen 配置，Claude 不启用。两者各最多调用一次；仅超时、连接、429、5xx 或无效响应进入 fallback。配置和 Secret 只来自环境变量，日志只记录 provider、错误类别、延迟和 request_id。

`xiaole_core/persona.md` 是新 Core 唯一人格来源，只描述小乐身份、简洁诚实风格及 Brain/Memory/Action 边界；不包含用户长期事实、工具全集、Secret 或旧行为学习 Prompt。

## Brain 数据流

1. 路由完成 JWT 校验并传入当前用户。
2. Context Repository 创建或校验会话并取得最多 12 条历史消息。
3. Intent Router 只决定目标系统。
4. conversation：Model Router 直接生成普通回答。
5. memory：Memory Gateway 调用乐知；Brain 仅做轻量表达整理。
6. action：Brain 形成 `notification.send` 结构化意图并调用 Action Gateway。
7. 保存本轮 user/assistant 消息并返回统一响应。

一次请求最多调用一个 Gateway。普通聊天在乐知或小可不可用时仍可工作。

## Memory Gateway

当前真实契约为本机 `POST http://127.0.0.1:8765/ask`：

```json
{"q":"最近有什么值得我关注的官方通知？","mode":"ask","context":[]}
```

成功响应核心字段为 `ok`、`question`、`answer`、`sources`、`flags`。远程鉴权头是 `X-KOS-Token`；loopback 当前允许无 Token。Gateway 允许通过环境变量配置 URL、可选 Token 和 timeout，不在日志或响应中泄漏 Token。

统一结果包含 `answer`、完整 `sources`、`confidence` 和小乐 `request_id`。乐知 `answer` 和 `sources` 是事实依据：小乐可以轻量整理表达，但不得增加结果中没有依据的新事实、资格结论或引用；sources 必须完整保留。Phase A 优先 grounded。若乐知不可用、超时、403、非 JSON 或 `ok=false`，Brain 明确说明知识系统暂不可用，不调用模型伪造检索结果。

## Action Gateway

真实接口为：

```text
POST /v1/tasks
GET  /v1/tasks/{task_id}
Authorization: Bearer <XIAOKE_API_TOKEN>
X-Request-ID: <request_id>
```

TaskCommand 使用真实字段：`idempotency_key`、`source_system`、`task_type`、`priority`、`target`、`parameters`、`risk_level`、`requires_confirmation`、`confirmation_token`、带时区 `requested_at`、`metadata`。Phase A 只允许 `notification.send`，其参数使用小可真实 `NotificationParameters`。

Gateway 创建任务后轮询状态，映射 `pending/running/success/failed/cancelled/dead`；本地验收默认 100ms 间隔、10 秒上限。仅 `success` 可返回成功摘要，失败或超时不得假成功。统一 ActionResult 只包含 task_id、status、summary、安全 evidence 和 request_id。BrainCore 不接触或暴露 Attempt、Dispatcher、Adapter、monitor-service、Bark、stdout、stderr 或 audit_events。

`requires_confirmation` 和 `confirmation_token` 保留未来扩展能力；Phase A 的测试通知为低风险且不要求确认。

## 错误、安全与兼容性

- Gateway 将 HTTP/解析异常转换为领域错误。
- 日志不记录完整 Prompt、Authorization、Token、Secret 或 Gateway 原始敏感响应。
- 自动化测试使用注入的 fake/MockTransport，禁止连接真实外部系统。
- 架构测试禁止 `xiaole_core` 导入 `agent`、`memory`、`modules.task_executor`、`modules.tool_manager`。
- SQL 边界测试证明新 Core 只读写 conversations/messages。
- 现有 `/chat`、`/chat/sse`、`/chat/stream` 和生产 UI 保持不变。

## TDD 与验收

严格按 Red → Green → Refactor 实施，覆盖 Prompt 指定的 32 项行为，并增加：未登录 401、合法 JWT 成功、非法 JWT 401、跨用户会话拒绝、同用户不同会话隔离。

自动化测试通过后依次执行：

- E2E A：真实 Core 普通对话，Memory/Action 未调用。
- E2E B：真实 Core 调用本机真实乐知 `/ask`，保留真实 sources；不得 Mock。
- E2E C：真实 Core 调用本地小可 HTTP API，小可 Notification 下游必须为 Mock；不得连接真实 monitor-service/Bark。

任何 E2E 失败只报告小乐侧结果，不修改乐知或小可。完成 A/B/C 后停止并输出验收报告；不启动 Phase B、生产部署、Web 切换、提交或 push。

## 已知接口差异

乐知远程鉴权使用 `X-KOS-Token` 而非 Bearer，且响应没有独立 request_id/confidence；由 Gateway 适配。小可完整查询响应包含内部 attempts/audit_events；Gateway 只消费完成映射所需字段，不向 Brain 暴露内部结构。以上均为普通适配差异，不构成架构硬冲突。
