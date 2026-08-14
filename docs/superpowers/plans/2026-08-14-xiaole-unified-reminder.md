# 小乐 2.0 统一提醒实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让小乐 2.0 通过 XiaoKe Action Core 完成统一提醒的创建、查询、详情、确认、暂停和取消，并严格执行时间、还款确认和隐私规则。

**Architecture:** 新增独立 Reminder Gateway 封装现有 Reminder API；新增确定性 Reminder Orchestrator 解析和校验对话命令；Brain Core 增加 reminder 分支。Action Core 是唯一存储和调度来源，旧提醒架构保持不变。

**Tech Stack:** Python 3.11、Pydantic v2、requests、标准库 `zoneinfo`、unittest。

## Global Constraints

- 仅修改小乐 2.0 `/v2/chat`；不得让它导入或调用旧 ReminderTool、ReminderManager、Scheduler 或旧提醒数据库。
- 所有提醒操作仅调用 XiaoKe Action Core Reminder API，不新增数据库、定时任务或 Bark 逻辑。
- 不修改 crontab，不直接调用 Bark URL。
- 创建固定 `source_system=xiaole`，类别仅为 `repayment`、`work`、`daily`。
- 时间按 `Asia/Shanghai` 解析并发送为带 `+08:00` 的 ISO 8601；缺失或歧义时不得猜测或调用 API。
- 含金额还款必须先 draft，只有同会话明确确认精确提醒 ID 后才调用 confirm。
- Token 仅从环境变量读取，不得进入源码、日志、响应或测试快照。
- 不提交、不推送、不部署；自动化测试不得连接真实外部服务。

---

### Task 1: Reminder API Gateway 与安全模型

**Files:**
- Create: `xiaole_core/gateways/reminder.py`
- Modify: `xiaole_core/schemas.py`, `xiaole_core/errors.py`
- Test: `tests/xiaole_core/test_reminder_gateway.py`

**Interfaces:**
- Produces: `ReminderGateway.create(command, request_id)`, `list(filters, request_id)`, `get(reminder_id, request_id)`, `confirm(...)`, `pause(...)`, `cancel(...)`。
- Produces: `ReminderCreateCommand` 和安全投影后的 `ReminderResult`。

- [ ] **Step 1:** 写失败测试，覆盖六个 API 路径、Bearer、`source_system=xiaole`、`+08:00`、过滤参数和安全错误映射。
- [ ] **Step 2:** 运行 `./venv/bin/python -m unittest tests.xiaole_core.test_reminder_gateway -v`，确认因模块缺失而失败。
- [ ] **Step 3:** 实现最小 Gateway、Pydantic 模型与领域错误，不记录请求体或原始异常。
- [ ] **Step 4:** 重跑聚焦测试并确认通过；执行 `git diff --check`。

### Task 2: 确定性提醒解析与业务编排

**Files:**
- Create: `xiaole_core/reminders.py`
- Test: `tests/xiaole_core/test_reminders.py`

**Interfaces:**
- Consumes: Task 1 的 `ReminderGateway` 和安全模型。
- Produces: `ReminderOrchestrator.handle(message, history, conversation_id, request_id, now=None) -> ReminderOutcome`。

- [ ] **Step 1:** 写失败测试，覆盖三类创建、缺日期/时间、歧义时间、提醒晚于事项、金额 draft 复述、明确确认、无草稿确认、查询/详情/暂停/取消。
- [ ] **Step 2:** 运行聚焦测试，确认缺少编排器导致预期失败。
- [ ] **Step 3:** 实现最小确定性语法：明确 ISO/中文年月日及今天/明天/后天，操作关键词、精确 ID、类别、金额和待确认历史恢复。
- [ ] **Step 4:** 重跑聚焦测试；确认所有拒绝路径的 Gateway 调用数为零。

### Task 3: Brain Core 路由与依赖注入

**Files:**
- Modify: `xiaole_core/intent.py`, `xiaole_core/schemas.py`, `xiaole_core/brain.py`, `xiaole_core/dependencies.py`
- Test: `tests/xiaole_core/test_intent.py`, `tests/xiaole_core/test_brain.py`, `tests/xiaole_core/test_dependencies.py`

**Interfaces:**
- Consumes: `ReminderOrchestrator.handle(...)`。
- Produces: `Intent.REMINDER` 和现有 `BrainResponse` 的安全 reminder 响应；不扩散私人字段到 diagnostics。

- [ ] **Step 1:** 写失败测试，验证提醒优先路由、Brain 只调用 Reminder Orchestrator、普通对话和测试通知不回归。
- [ ] **Step 2:** 运行三个聚焦测试并确认预期失败。
- [ ] **Step 3:** 增加 reminder intent 分支并在依赖装配中共享 Action Core URL/Token/timeout。
- [ ] **Step 4:** 重跑测试，确认现有 Action Gateway 行为和响应 schema 不变。

### Task 4: 配置、架构边界与部署文档

**Files:**
- Modify: `.env.example`, `README.md`
- Modify: `tests/xiaole_core/test_architecture_boundaries.py`
- Create or modify: `tests/xiaole_core/test_reminder_security.py`

**Interfaces:**
- Documents: `XIAOKE_ACTION_URL`, `XIAOKE_API_TOKEN`, `XIAOKE_ACTION_TIMEOUT_SECONDS`。
- Guards: 小乐 2.0 不得导入旧提醒、cron 或 Bark 实现。

- [ ] **Step 1:** 写失败的边界/脱敏测试，覆盖 forbidden imports、Token/正文/原始错误不泄漏及未配置时零网络调用。
- [ ] **Step 2:** 运行聚焦测试并确认预期失败。
- [ ] **Step 3:** 最小更新配置示例和 README 的本地验证、部署、回滚与风险说明。
- [ ] **Step 4:** 重跑安全和架构测试；检查 `.env` 未被修改，源码无 Token 值。

### Task 5: 全量本地验证与验收脚本

**Files:**
- Create: `scripts/run_xiaole_reminder_acceptance.py`
- Test: `tests/xiaole_core/test_reminder_acceptance_script.py`

**Interfaces:**
- Produces: 默认 dry-run 的验收脚本；只有显式参数才允许 Action Core 创建“部署验收”提醒并立即 GET、等待观澜人工核对、取消。

- [ ] **Step 1:** 写失败测试，证明默认模式只输出脱敏计划且零网络调用；生产模式要求显式 URL/Token 环境和未来时间。
- [ ] **Step 2:** 运行聚焦测试并确认预期失败。
- [ ] **Step 3:** 实现安全验收脚本，禁止还款/金额、默认 dry-run、创建后使用 `finally` 尝试取消，绝不调用 Bark。
- [ ] **Step 4:** 运行聚焦测试和 `./venv/bin/python -m unittest discover -s tests -v`。
- [ ] **Step 5:** 运行 `git diff --check`、编译检查及变更范围审计；不执行真实验收，等待用户单独授权。
