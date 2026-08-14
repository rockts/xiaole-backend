# 小乐 2.0 统一提醒接入设计

## 目标与范围

仅为小乐 2.0 `/v2/chat` 接入 XiaoKe Action Core 统一提醒中心。小乐通过 Action Core Reminder API 创建、查询、读取详情、确认、暂停和取消提醒，固定使用 `source_system=xiaole`。

旧版 `XiaoLeAgent`、`ReminderTool`、小乐提醒数据库、Scheduler、旧提醒路由和前端保持不变；不迁移旧数据，也不让小乐 2.0 调用旧提醒实现。项目不新增数据库、定时任务或 Bark 发送逻辑，不修改 crontab，不直接调用 Bark URL。

## 架构

在现有 `xiaole_core` 内增加三个边界清晰的单元：

1. `ReminderGateway`：唯一负责 Action Core Reminder API 的 HTTP 通信、认证、响应校验和安全错误归类。
2. `ReminderOrchestrator`：负责提醒命令解析、业务校验、绝对时间解析、会话确认状态和用户安全文案。
3. Brain Core 提醒分支：由 `IntentRouter` 将提醒请求路由到编排器，再把结果写入现有会话历史。

`ReminderGateway` 与现有 `ActionGateway` 共享 `XIAOKE_ACTION_URL`、`XIAOKE_API_TOKEN` 和 `XIAOKE_ACTION_TIMEOUT_SECONDS` 配置，但职责独立。现有 `ActionGateway` 的测试通知行为不改变。

## 提醒调用契约

支持以下接口：

- `POST /v1/reminders`
- `GET /v1/reminders`
- `GET /v1/reminders/{id}`
- `POST /v1/reminders/{id}/confirm`
- `POST /v1/reminders/{id}/pause`
- `POST /v1/reminders/{id}/cancel`

创建请求字段与现有 `xiaoke-reminder` CLI 一致：

- `idempotency_key`：以 `xiaole:` 开头，并结合请求 ID，避免重复创建。
- `source_system`：固定为 `xiaole`。
- `title`：提醒事项或还款收款方。
- `category`：仅允许 `repayment`、`work`、`daily`。
- `event_at`、`notify_at`：带 `+08:00` 的 ISO 8601 时间。
- `timezone`：固定为 `Asia/Shanghai`。
- `amount`：仅还款提醒可选；保留为字符串，不使用浮点数。
- `currency`：固定为 `CNY`。
- `notification_title`、`notification_body`：仅发送至 Action Core，不写入诊断信息或前端元数据。
- `metadata`：只包含非敏感的 `channel=xiaole-v2`、会话 ID 和请求 ID。

查询允许按 Action Core 契约过滤 `status` 和 `category`。详情与状态操作必须使用 Action Core 返回的精确提醒 ID，不根据序号或文本猜测目标。

## 对话与时间规则

提醒意图优先使用确定性规则识别。编排器从当前消息和最近会话历史中提取操作、类别、标题、日期、事项时间、Bark 提醒时间、收款方、金额和提醒 ID。

时间规则如下：

- 所有时间按 `Asia/Shanghai` 解析并发送为 `+08:00` ISO 8601。
- 支持明确的绝对日期时间，以及“今天”“明天”“后天”等带明确时间的相对日期。
- 仅有钟点、星期但缺少可唯一确定的日期，或存在多个合理解释时，返回追问且不调用 Action Core。
- 不为缺失的事项时间或 Bark 时间自行填充默认值。
- 时间必须有效，Bark 时间不得晚于事项时间；无效时只解释并追问。

工作和日常提醒在必要信息完整后直接调用创建接口。创建成功只回报 Action Core 返回的提醒 ID 与状态，不声称 Bark 已推送或送达。

## 还款确认流程

含金额的 `repayment` 创建请求由 Action Core 自动保存为 `draft`。小乐收到响应后必须复述：

- 收款方
- 金额与币种
- 还款日期和时间
- Bark 提醒日期和时间
- Action Core 返回的提醒 ID 与 `draft` 状态

同时明确询问用户是否确认启用。只有同一用户、同一会话存在待确认草稿，且用户随后明确表达“确认”“确认启用该提醒”等肯定语义时，才能对该精确 ID 调用 `POST /confirm`。

如果用户拒绝，则不确认；只有用户明确要求取消时才调用 `/cancel`。如果会话中没有唯一待确认草稿，单独一句“确认”不得调用 API，必须询问具体提醒 ID。

待确认状态不新增数据库表。它由 Action Core 的草稿状态作为事实来源，并结合当前会话历史中小乐刚刚返回的提醒 ID 进行恢复。这样服务重启后仍可从对话历史和 Action Core 详情核对，不产生第二份业务状态。

## 查询和管理

- “查询/列出提醒”调用 `GET /v1/reminders`，可带明确的类别或状态过滤。
- “查看提醒 ID”调用 `GET /v1/reminders/{id}`。
- “暂停提醒 ID”调用 `/pause`。
- “取消提醒 ID”调用 `/cancel`。
- “确认提醒 ID”仅用于明确确认 draft；不得将普通确认语句误判为提醒确认。

用户响应只展示管理所需的最小字段：提醒 ID、标题、类别、事项时间、提醒时间和状态。金额只在还款草稿确认复述或用户明确查询该提醒时展示。`notification_body`、服务端错误详情、认证信息和内部审计内容不返回给前端。

## 错误处理与安全

- Token 仅从 `XIAOKE_API_TOKEN` 读取，通过 `Authorization: Bearer` 请求头发送。
- 未配置 URL 或 Token 时不发网络请求，向用户返回统一的“提醒服务暂时不可用”。
- 网关不记录请求头、Token、完整请求体、金额、通知正文或服务端原始错误。
- HTTP 401/403、404、409、422、超时、连接失败和无效响应映射为有限的安全错误类型。
- Brain Core 的 `answer` 可包含当前操作必要的业务信息，但 `diagnostics`、安全日志和异常信息不得包含私人数据。
- Action Core 返回失败时不降级到旧提醒、cron 或 Bark。

## 代码边界与兼容性

预计新增：

- `xiaole_core/gateways/reminder.py`：Reminder API 客户端。
- `xiaole_core/reminders.py`：确定性解析、校验、编排与文案。
- `tests/xiaole_core/test_reminder_gateway.py`：API 契约及脱敏测试。
- `tests/xiaole_core/test_reminders.py`：解析和业务规则测试。

预计修改：

- `xiaole_core/schemas.py`：提醒意图、命令和安全响应模型。
- `xiaole_core/intent.py`：提醒意图路由。
- `xiaole_core/brain.py`：提醒分支和对话历史协作。
- `xiaole_core/dependencies.py`：构建并注入 Reminder Gateway/Orchestrator。
- `.env.example`、`README.md` 或部署文档：同步配置与部署说明。
- 现有 Brain、Intent、Gateway 和 API 测试：覆盖兼容性。

不修改旧提醒文件，不改 Action Core，不增加 Python 依赖。

## 测试与验收

本地自动化测试采用 TDD，至少覆盖：

- 三类提醒与六个 Reminder API 操作。
- `source_system=xiaole`、Bearer 认证和幂等键。
- 所有提交时间包含 `+08:00`，时区固定 `Asia/Shanghai`。
- 缺日期、缺提醒时间、歧义时间和无效时间均不调用 API。
- 工作、日常创建后直接启用状态展示。
- 含金额还款先 draft，完整复述后才允许明确确认。
- 无待确认草稿、跨会话或含糊“确认”不调用 confirm。
- 创建成功文案不包含 Bark 已送达声明。
- 查询、详情、暂停、取消使用精确 ID。
- Token、通知正文、金额及原始错误不进入诊断或日志。
- 旧提醒架构未被小乐 2.0 引用，现有测试不回归。

本地验证使用模拟 HTTP transport，不连接生产 Action Core。代码与本地测试完成后，生产式验收是单独外部写入门槛：创建一条未来的非还款“部署验收”提醒，读取详情确认落库，检查乐可观澜显示 `source_system=xiaole`，随后立即取消并核对状态。该步骤必须在用户再次明确授权后执行，并确保提醒时间留有足够余量，避免进入 Bark 调度窗口。

## 部署与回滚

生产部署前需在小乐后端安全环境中配置 `XIAOKE_ACTION_URL`、`XIAOKE_API_TOKEN` 和 `XIAOKE_ACTION_TIMEOUT_SECONDS`，验证容器到 Action Core 的网络可达性。不得把 Token 写入仓库或命令输出。

部署沿用现有 GitHub Actions 构建 Docker 镜像及 NAS 容器更新流程。主要风险是意图误判、日期解析错误、重复创建、确认错对象、Action Core 不可达和隐私字段泄漏。对应控制为确定性路由、严格缺失/歧义校验、请求级幂等键、会话与精确 ID 绑定、失败闭合和安全响应投影。

回滚仅需恢复上一版小乐后端镜像；Action Core 中已创建的提醒不会因小乐回滚而丢失，必要时通过统一 Reminder API 显式暂停或取消。旧提醒系统不受本次改动影响。
