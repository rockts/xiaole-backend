# 小乐 AI 管家 - 项目概览

## 项目简介

小乐 AI 管家是一个基于 FastAPI + PostgreSQL 构建的个人 AI 助手后端系统，提供智能对话、记忆管理、任务管理、提醒等功能。

## 技术栈

- **后端框架**：FastAPI
- **数据库**：PostgreSQL
- **ORM**：SQLAlchemy
- **任务调度**：APScheduler
- **AI 能力**：DeepSeek API / Claude API
- **部署**：Docker + NAS + Cloudflare Tunnel

## 核心模块

### 1. Agent 核心 (`agent.py`)
- `XiaoLeAgent`：主 Agent 类，负责对话、工具调用、任务管理
- 支持多轮对话、上下文理解、工具自动调用
- 支持复杂任务识别、拆解和执行

### 2. 记忆管理 (`memory.py`)
- 长期记忆存储和检索
- 语义搜索能力
- 记忆分类：facts、conversation、image、document、schedule 等
- 智能提取用户消息中的关键事实

### 3. 对话管理 (`conversation.py`)
- 会话管理
- 对话历史存储和检索
- 支持图片消息

### 4. 工具系统 (`tools/`)
- 天气查询 (`weather_tool.py`)
- 系统信息 (`system_tool.py`)
- 时间查询 (`time_tool.py`)
- 计算器 (`calculator_tool.py`)
- 提醒管理 (`reminder_tool.py`)
- 搜索 (`search_tool.py`)
- 文件操作 (`file_tool.py`)
- 任务管理 (`task_tool.py`)
- 视觉识别 (`vision_tool.py`)
- 人脸注册 (`register_face_tool.py`)

### 5. 任务管理 (`task_manager.py`, `task_executor.py`)
- 复杂任务识别
- 任务拆解为步骤
- 任务执行和状态跟踪
- 支持用户确认和恢复

### 6. 提醒管理 (`reminder_manager.py`)
- 提醒创建、查询、删除
- 定时提醒推送（WebSocket）
- 优先级管理

### 7. 行为分析 (`behavior_analytics.py`)
- 用户行为数据记录
- 会话行为分析

### 8. 模式学习 (`pattern_learning.py`)
- 从用户消息中学习使用模式
- 个性化服务

### 9. 主动问答 (`proactive_qa.py`)
- 检测对话中的信息缺失
- 主动生成追问

### 10. 对话增强 (`dialogue_enhancer.py`)
- 对话质量提升
- 响应风格优化

## API 路由 (`routers/`)

- `auth.py`：用户认证
- `chat.py`：对话接口
- `memories.py`：记忆管理
- `reminders.py`：提醒管理
- `tasks.py`：任务管理
- `tools.py`：工具调用
- `analytics.py`：数据分析
- `documents.py`：文档管理
- `voice.py`：语音接口
- `schedule.py`：日程管理
- `feedback.py`：反馈收集
- `faces.py`：人脸管理
- `dashboard.py`：仪表盘
- `vision.py`：视觉识别

## 数据库结构

### 主要表
- `memories`：记忆表
- `conversations`：会话表
- `messages`：消息表
- `reminders`：提醒表
- `tasks`：任务表
- `task_steps`：任务步骤表
- `documents`：文档表
- `feedback`：反馈表
- `face_encodings`：人脸编码表

## 部署信息

- **API 地址**：https://api.leke.xyz
- **Docker Hub**：rockts/xiaole-backend
- **部署方式**：GitHub Actions 自动构建和推送，NAS 通过 Watchtower 自动拉取更新

## 相关仓库

- [xiaole-web](https://github.com/rockts/xiaole-web) - 前端 UI
- [xiaole-ai](https://github.com/rockts/xiaole-ai) - 项目文档

## 版本历史

- **v0.8.0**：任务管理功能
- **v0.6.0**：对话质量增强、响应风格支持
- **v0.5.0**：提醒工具、搜索工具、文件工具
- **v0.4.0**：工具管理系统
- **v0.3.0**：行为分析、模式学习、主动问答

