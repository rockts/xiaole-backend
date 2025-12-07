# 开发规则（Agent 遵守）

1. 不得修改文件结构，除非用户明确指示
2. 不得删除用户代码
3. 所有改动前必须生成 diff，用户确认后才能应用
4. 遵守 project-overview.md 描述的目录和模块结构
5. 遵守 task-basic-rules.md 的任务执行规则
6. 所有工具调用必须遵守 tools.md 定义的接口
7. 避免自动重构整个项目
8. 每次提交或修改必须记录操作说明
9. **文档管理规则**：
   - Agent 相关文档（xiaole-agent-context/*）必须保留在当前仓库
   - 详细文档（使用指南、教程等）应移到 xiaole-ai 仓库
   - 项目说明（README.md）保留在当前仓库
   - 开发上下文（docs/DEV_CONTEXT.md）保留在当前仓库（iCloud 同步）
   - **创建新文档时**：
     - **方式1（推荐）**：直接使用 `write` 工具创建到 `../xiaole-ai/backend/` 或 `../xiaole-ai/frontend/` 目录
       - 后端文档：`../xiaole-ai/backend/setup/` 或 `../xiaole-ai/backend/development/`
       - 前端文档：`../xiaole-ai/frontend/setup/` 或 `../xiaole-ai/frontend/development/` 等
     - **方式2**：使用 `./scripts/create-doc.sh <类型> <名称>` 脚本创建
   - **前端仓库**：复制 `scripts/create-doc.sh` 到前端仓库，脚本会自动识别仓库类型
