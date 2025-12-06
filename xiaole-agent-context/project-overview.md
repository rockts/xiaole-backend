# Xiaole 项目概览（Agent 参考用）

## 仓库结构

- xiaole-web/       前端 UI 相关
    └─ src/        页面、组件、样式
    └─ .cursorrules 前端 Agent 规则

- xiaole-backend/   后端逻辑
    └─ main.py     应用入口
    └─ agent.py    AI Agent 核心
    └─ modules/   功能模块（行为分析、任务管理、工具管理等）
    └─ routers/    API 路由
    └─ tools/      Agent 工具
    └─ xiaole-agent-context/ Agent 上下文（必须保留）
    └─ .cursorrules 后端 Agent 规则
    └─ docs/       仅保留 DEV_CONTEXT.md（iCloud 同步）
    └─ README.md   项目说明（必须保留）

- xiaole-ai/       项目文档库
    └─ backend/    后端详细文档（使用指南、设置教程等）
    └─ frontend/   前端文档
    └─ shared/     共享文档

## 数据流和 API

- 前端通过 REST / WebSocket 调用后端 API
- 后端处理任务、状态机、记忆、工具调用
- 所有跨仓库约定在 xiaole-agent-context 文件中说明

## 部署

- 前端部署 Cloudflare Pages
- 后端部署 NAS + Cloudflare Tunnel
- Docs 可选部署为静态文档站
