# 根目录整理方案

## 当前问题

根目录有 **37 个文件/目录**，文件较多，结构不够清晰。

## 整理方案

### 方案 A：创建 `src/` 目录（推荐）

将核心业务逻辑文件移到 `src/` 目录：

```
xiaole-backend/
├── main.py                    # 应用入口（保留在根目录）
├── config.py                  # 配置（保留在根目录）
├── logger.py                  # 日志（保留在根目录）
├── dependencies.py            # 依赖注入（保留在根目录）
│
├── src/                       # 核心业务逻辑
│   ├── agent.py              # AI Agent
│   ├── memory.py             # 记忆管理
│   ├── conversation.py       # 对话管理
│   ├── scheduler.py          # 定时任务
│   ├── auth.py               # 认证
│   ├── error_handler.py      # 错误处理
│   │
│   ├── core/                 # 核心功能模块
│   │   ├── behavior_analytics.py
│   │   ├── conflict_detector.py
│   │   ├── dialogue_enhancer.py
│   │   ├── document_summarizer.py
│   │   ├── enhanced_intent.py
│   │   ├── face_manager.py
│   │   ├── learning.py
│   │   ├── pattern_learning.py
│   │   ├── proactive_chat.py
│   │   ├── proactive_qa.py
│   │   ├── reminder_manager.py
│   │   ├── semantic_search.py
│   │   ├── task_executor.py
│   │   ├── task_manager.py
│   │   └── tool_manager.py
│   └── ...
│
├── routers/                   # API 路由（保持不变）
├── tools/                     # Agent 工具（保持不变）
├── scripts/                   # 工具脚本（保持不变）
└── ...
```

### 方案 B：创建 `core/` 和 `utils/` 目录

```
xiaole-backend/
├── main.py                    # 应用入口
├── config.py                  # 配置
├── logger.py                  # 日志
├── dependencies.py            # 依赖注入
│
├── core/                      # 核心业务逻辑
│   ├── agent.py
│   ├── memory.py
│   ├── conversation.py
│   ├── scheduler.py
│   └── ...
│
├── utils/                     # 辅助工具模块
│   ├── behavior_analytics.py
│   ├── conflict_detector.py
│   ├── dialogue_enhancer.py
│   ├── document_summarizer.py
│   ├── enhanced_intent.py
│   ├── face_manager.py
│   ├── learning.py
│   ├── pattern_learning.py
│   ├── proactive_chat.py
│   ├── proactive_qa.py
│   ├── reminder_manager.py
│   ├── semantic_search.py
│   ├── task_executor.py
│   ├── task_manager.py
│   └── tool_manager.py
│
└── ...
```

### 方案 C：最小改动（仅整理辅助模块）

保持核心文件在根目录，只整理辅助模块：

```
xiaole-backend/
├── main.py                    # 应用入口
├── agent.py                   # AI Agent（核心）
├── memory.py                  # 记忆管理（核心）
├── conversation.py            # 对话管理（核心）
├── scheduler.py               # 定时任务（核心）
├── config.py                  # 配置
├── logger.py                  # 日志
├── dependencies.py            # 依赖注入
├── auth.py                    # 认证
│
├── modules/                   # 功能模块
│   ├── behavior_analytics.py
│   ├── conflict_detector.py
│   ├── dialogue_enhancer.py
│   ├── document_summarizer.py
│   ├── enhanced_intent.py
│   ├── face_manager.py
│   ├── learning.py
│   ├── pattern_learning.py
│   ├── proactive_chat.py
│   ├── proactive_qa.py
│   ├── reminder_manager.py
│   ├── semantic_search.py
│   ├── task_executor.py
│   ├── task_manager.py
│   └── tool_manager.py
│
└── ...
```

## 推荐方案

**推荐方案 C（最小改动）**：
- 保持核心文件在根目录（main.py, agent.py, memory.py 等）
- 将功能模块移到 `modules/` 目录
- 保持配置文件在根目录
- 影响最小，改动最少

## 需要更新的文件

整理后需要更新以下文件的导入路径：
- `main.py` - 更新模块导入
- `routers/*.py` - 更新模块导入
- `tools/*.py` - 更新模块导入
- 其他引用这些模块的文件

## 注意事项

1. 需要更新所有导入语句
2. 需要测试确保功能正常
3. 需要更新 `PROJECT-STRUCTURE.md`
4. 需要更新 `xiaole-agent-context/project-overview.md`

