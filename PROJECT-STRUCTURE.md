# 项目目录结构

> 最后更新: 2025-12-07
> 
> **更新**: 已整理根目录，功能模块移至 `modules/` 目录

## 目录结构

```
xiaole-backend/
├── .cursorrules                 # Cursor AI 配置（自动读取上下文）
├── .gitignore                   # Git 忽略规则
├── README.md                    # 项目说明
├── requirements.txt             # Python 依赖
├── Dockerfile                   # Docker 构建文件
├── docker-compose.yml          # Docker Compose 配置
│
├── main.py                      # 应用入口
├── agent.py                     # AI Agent 核心逻辑
├── config.py                    # 配置管理
├── auth.py                      # 认证模块
├── conversation.py              # 对话管理
├── memory.py                    # 记忆管理
├── scheduler.py                 # 定时任务调度
├── dependencies.py              # 依赖注入
├── error_handler.py             # 错误处理
├── db_setup.py                 # 数据库设置
│
├── modules/                     # 功能模块
│   ├── behavior_analytics.py   # 行为分析
│   ├── conflict_detector.py    # 冲突检测
│   ├── dialogue_enhancer.py    # 对话增强
│   ├── document_summarizer.py  # 文档摘要
│   ├── enhanced_intent.py      # 意图增强
│   ├── face_manager.py         # 人脸管理
│   ├── learning.py             # 学习模块
│   ├── pattern_learning.py     # 模式学习
│   ├── proactive_chat.py       # 主动聊天
│   ├── proactive_qa.py         # 主动问答
│   ├── reminder_manager.py    # 提醒管理
│   ├── semantic_search.py      # 语义搜索
│   ├── task_executor.py        # 任务执行器
│   ├── task_manager.py         # 任务管理
│   └── tool_manager.py         # 工具管理
│
├── xiaole-agent-context/        # Agent 规则（必须保留）
│   ├── persona.md              # Agent 角色定义
│   ├── dev-rules.md            # 开发规则
│   ├── project-overview.md     # 项目概览
│   ├── tools.md                # 工具说明
│   └── task-basic-rules.md     # 任务规则
│
├── docs/                        # 文档目录（仅保留必要文件）
│   ├── .gitkeep                # 保持目录存在
│   ├── DEV_CONTEXT.md          # 开发上下文（符号链接，iCloud 同步）
│   └── DEV_CONTEXT.md.example  # 模板文件
│
├── scripts/                     # 工具脚本
│   ├── setup-context.sh        # 设置开发上下文
│   ├── verify-context.sh       # 验证上下文设置
│   ├── check-sync.sh           # 检查 iCloud 同步
│   ├── create-doc.sh           # 创建文档到文档库
│   ├── move-docs-to-repo.sh    # 迁移文档到文档库
│   ├── debug_recall.py         # 调试工具
│   └── debug_tags.py           # 调试工具
│
├── routers/                     # API 路由
│   ├── __init__.py
│   ├── auth.py                 # 认证路由
│   ├── chat.py                 # 聊天路由
│   ├── memories.py             # 记忆路由
│   ├── reminders.py            # 提醒路由
│   ├── tasks.py                # 任务路由
│   ├── documents.py            # 文档路由
│   ├── tools.py                # 工具路由
│   ├── voice.py                # 语音路由
│   ├── vision.py               # 视觉路由
│   └── ...
│
├── tools/                       # Agent 工具
│   ├── __init__.py
│   ├── system_tool.py          # 系统工具
│   ├── weather_tool.py         # 天气工具
│   ├── search_tool.py          # 搜索工具
│   ├── file_tool.py            # 文件工具
│   ├── reminder_tool.py        # 提醒工具
│   ├── task_tool.py            # 任务工具
│   ├── vision_tool.py          # 视觉工具
│   └── ...
│
├── db_migrations/               # 数据库迁移
│   ├── 001_create_reminders_tables.sql
│   ├── 002_add_indexes_v0.6.0.sql
│   └── ...
│
├── static/                      # 静态文件
│   ├── index.html              # 前端页面
│   ├── css/                    # 样式文件
│   ├── js/                     # JavaScript 文件
│   ├── images/                 # 图片资源
│   └── sounds/                 # 音频文件
│
├── logs/                        # 日志目录
│   └── xiaole_ai.log           # 应用日志
│
├── uploads/                     # 上传文件目录
└── files/                       # 文件存储目录
```

## 文件分类

### 核心代码文件
- `main.py` - FastAPI 应用入口
- `agent.py` - AI Agent 核心逻辑
- `memory.py` - 记忆管理
- `conversation.py` - 对话管理
- `scheduler.py` - 定时任务
- `config.py` - 配置管理
- `dependencies.py` - 依赖注入
- `error_handler.py` - 错误处理

### 功能模块（modules/）
- `behavior_analytics.py` - 行为分析
- `conflict_detector.py` - 冲突检测
- `dialogue_enhancer.py` - 对话增强
- `document_summarizer.py` - 文档摘要
- `enhanced_intent.py` - 意图增强
- `face_manager.py` - 人脸管理
- `learning.py` - 学习模块
- `pattern_learning.py` - 模式学习
- `proactive_chat.py` - 主动聊天
- `proactive_qa.py` - 主动问答
- `reminder_manager.py` - 提醒管理
- `semantic_search.py` - 语义搜索
- `task_executor.py` - 任务执行器
- `task_manager.py` - 任务管理
- `tool_manager.py` - 工具管理

### Agent 规则（必须保留）
- `xiaole-agent-context/*` - Agent 上下文文件

### 文档文件
- `README.md` - 项目说明（保留）
- `docs/DEV_CONTEXT.md` - 开发上下文（符号链接，iCloud 同步）
- 详细文档 → `xiaole-ai/backend/`

### 工具脚本
- `scripts/setup-context.sh` - 设置开发上下文
- `scripts/verify-context.sh` - 验证设置
- `scripts/check-sync.sh` - 检查 iCloud 同步
- `scripts/create-doc.sh` - 创建文档到文档库
- `scripts/move-docs-to-repo.sh` - 迁移文档

## 已清理的文件

- ✅ `__pycache__/` - Python 缓存目录（已删除）
- ✅ `.DS_Store` - macOS 系统文件（已删除）
- ✅ 所有缓存文件已清理

## 注意事项

1. **不要提交的文件**：
   - `__pycache__/` - Python 缓存
   - `.DS_Store` - macOS 系统文件
   - `docs/DEV_CONTEXT.md` - 开发上下文（iCloud 同步）
   - `.env` - 环境变量（包含敏感信息）

2. **必须保留的文件**：
   - `xiaole-agent-context/*` - Agent 规则
   - `README.md` - 项目说明
   - `docs/DEV_CONTEXT.md.example` - 模板文件

3. **文档管理**：
   - 详细文档应使用 `./scripts/create-doc.sh` 创建到 `xiaole-ai` 仓库
   - 不要在当前仓库的 `docs/` 目录创建详细文档

