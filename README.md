# Xiaole Backend

小乐 AI 助手后端项目 - FastAPI + PostgreSQL

## 🚀 技术栈

- **FastAPI** - 现代高性能 Web 框架
- **SQLAlchemy** - Python ORM
- **PostgreSQL** - 关系型数据库
- **APScheduler** - 定时任务调度
- **OpenAI API** - AI 对话能力

## 📦 快速开始

### 本地开发

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填写必要的配置

# 启动服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Docker 部署

```bash
# 构建镜像
docker build -t xiaole-backend .

# 运行容器
docker run -d -p 8000:8000 --env-file .env xiaole-backend
```

## 🌐 API 端点

- `GET /health` - 健康检查
- `POST /token` - 用户登录
- `GET /sessions` - 获取会话列表
- `POST /chat` - 发送消息
- `GET /memory/{user_id}` - 获取记忆
- `GET /documents/users/{user_id}` - 获取文档
- `GET /tasks/users/{user_id}` - 获取任务
- 统一提醒由小乐 2.0 通过 Action Core 提供；旧网页提醒 API 已退役

## 🏗️ 项目结构

```
xiaole-backend/
├── main.py              # 应用入口
├── agent.py             # AI Agent 核心逻辑
├── memory.py            # 记忆管理
├── conversation.py      # 对话管理
├── scheduler.py         # 定时任务
├── routers/             # API 路由
├── tools/               # Agent 工具
├── db_migrations/       # 数据库迁移
├── Dockerfile           # Docker 构建
├── docker-compose.yml   # Docker Compose
└── requirements.txt     # Python 依赖
```

## 🚢 部署

项目部署到 **NAS + Cloudflare Tunnel**：

- API 地址: https://api.leke.xyz
- Docker Hub: rockts/xiaole-backend

### GitHub Actions 自动部署

推送到 `main` 分支时自动：
1. 构建 Docker 镜像
2. 推送到 Docker Hub
3. NAS 通过 Watchtower 自动拉取更新

## 🔗 相关仓库

- [xiaole-web](https://github.com/rockts/xiaole-web) - 前端 UI
- [xiaole-ai](https://github.com/rockts/xiaole-ai) - 项目文档

## 📄 License

MIT
# 小乐 2.0 Core Phase A

实验入口为 `POST /api/v2/chat`，必须使用现有小乐 JWT：

```json
{"message":"你好，今天我们做什么？","conversation_id":null,"attachments":[]}
```

新 Core 位于 `xiaole_core/`，只负责 conversation、memory、action 三类编排。长期知识统一通过乐知 `POST /ask`，执行统一通过小可 `POST /v1/tasks` 与任务状态查询；旧聊天接口和生产 Web 不切换。

本地配置见 `.env.example` 中的 `LEZHI_MEMORY_*`、`XIAOKE_ACTION_*` 和 `XIAOKE_API_TOKEN`。自动化测试命令：

```bash
./venv/bin/python -m unittest discover -s tests -t . -v
```

三个本地验收入口：

```bash
./venv/bin/python scripts/run_xiaole_core_e2e.py conversation
./venv/bin/python scripts/run_xiaole_core_e2e.py memory
./venv/bin/python scripts/run_xiaole_core_e2e.py action
```

`action` 模式只启动临时小可数据库和本机 Mock Notification 下游，不得用于真实 Bark 验收。
# 小乐 2.0 统一提醒

`/api/v2/chat` 通过 XiaoKe Action Core 的 `/v1/reminders` 接口管理统一提醒。配置复用 `XIAOKE_ACTION_URL`、`XIAOKE_API_TOKEN` 和 `XIAOKE_ACTION_TIMEOUT_SECONDS`；Token 必须由安全环境注入。

小乐 2.0 不写入旧提醒数据库，不创建定时任务，也不直接调用 Bark。工作和日常提醒可直接启用；含金额还款提醒先创建为 draft，并在用户明确确认后启用。创建成功仅代表 Action Core 已接受或保存提醒，不代表 Bark 已送达。

本地验证：

```bash
./venv/bin/python -m unittest tests.xiaole_core.test_reminder_gateway tests.xiaole_core.test_reminders tests.xiaole_core.test_reminder_security -v
```

生产部署继续使用现有 GitHub Actions 镜像构建和 NAS 容器更新流程。部署前验证容器到 Action Core 的网络可达性；回滚时恢复上一版后端镜像。Action Core 中已创建的提醒需通过 Reminder API 单独暂停或取消。
