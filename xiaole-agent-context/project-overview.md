# Xiaole 项目概览（Agent 参考用）

## 仓库结构

- xiaole-web/       前端 UI 相关
    └─ src/        页面、组件、样式
    └─ .cursorrules 前端 Agent 规则

- xiaole-backend/   后端逻辑
    └─ src/        后端代码、任务引擎
    └─ xiaole-agent-context/ Agent 上下文
    └─ .cursorrules 后端 Agent 规则
    └─ docs/       文档文件夹（可选）

- xiaole-ai/       历史文档与归档

## 数据流和 API

- 前端通过 REST / WebSocket 调用后端 API
- 后端处理任务、状态机、记忆、工具调用
- 所有跨仓库约定在 xiaole-agent-context 文件中说明

## 部署

- 前端部署 Cloudflare Pages
- 后端部署 NAS + Cloudflare Tunnel
- Docs 可选部署为静态文档站
