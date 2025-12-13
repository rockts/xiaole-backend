from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from typing import List
import os
import traceback

from routers import (
    auth, chat, memories, reminders, tasks,
    tools, analytics, documents, voice,
    schedule, feedback, faces, dashboard, vision
)
from dependencies import (
    get_reminder_manager, get_scheduler, get_xiaole_agent
)
from config import STATIC_DIR, UPLOADS_DIR, FILES_DIR
from logger import logger

app = FastAPI(
    title="小乐 AI 管家",
    description="个人 AI 助手系统",
    version="0.8.0",
)

# 全局异常处理器


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器，确保所有异常都能被捕获并返回正确的响应"""
    error_detail = str(exc)
    error_traceback = traceback.format_exc()

    logger.error(
        f"❌ 未捕获的异常: {error_detail}\n"
        f"请求路径: {request.url.path}\n"
        f"请求方法: {request.method}\n"
        f"异常堆栈:\n{error_traceback}"
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "服务器内部错误，请稍后重试",
            "error": error_detail,
            "path": str(request.url.path)
        }
    )

# 配置CORS
# 注意：当 allow_credentials=True 时，不能使用 allow_origins=["*"]
# 必须明确指定允许的域名
allowed_origins = [
    "https://ai.leke.xyz",
    "https://xiaole.app",
    "https://www.xiaole.app",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    # 本地局域网前端
    "http://192.168.88.104:3000",
]
# 如果环境变量设置了额外域名，添加到列表中
extra_origins = os.getenv("CORS_ORIGINS", "").split(",")
if extra_origins and extra_origins[0]:
    allowed_origins.extend([origin.strip()
                           for origin in extra_origins if origin.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 自定义StaticFiles类，禁用缓存


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = (
            "no-cache, no-store, must-revalidate"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


# 自定义StaticFiles类，添加CORS头（用于uploads等静态资源）
class CORSStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        # 添加CORS头，允许前端跨域访问图片
        response.headers["Access-Control-Allow-Origin"] = "https://ai.leke.xyz"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response


# 挂载静态文件目录
app.mount(
    "/static",
    NoCacheStaticFiles(directory=STATIC_DIR),
    name="static"
)
app.mount("/uploads", CORSStaticFiles(directory=UPLOADS_DIR), name="uploads")
if os.path.exists(FILES_DIR):
    app.mount("/files", StaticFiles(directory=FILES_DIR), name="files")

# WebSocket连接管理器


class ConnectionManager:
    """管理WebSocket连接"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """接受新连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"✅ WebSocket客户端已连接，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                f"👋 WebSocket客户端已断开，当前连接数: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """广播消息给所有连接的客户端"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"❌ 发送消息失败: {e}")
                disconnected.append(connection)

        # 清理断开的连接
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)


websocket_manager = ConnectionManager()


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    # 设置ReminderManager的WebSocket推送回调
    reminder_manager = get_reminder_manager(websocket_manager.broadcast)

    # 设置事件循环，使 ReminderManager 可以在后台线程中推送 WebSocket 消息
    import asyncio
    loop = asyncio.get_event_loop()
    reminder_manager.set_loop(loop)

    # 启动提醒调度器
    scheduler = get_scheduler()
    scheduler.start()
    logger.info("✅ 提醒调度器已启动")
    logger.info("✅ WebSocket推送已配置")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理"""
    scheduler = get_scheduler()
    scheduler.stop()
    logger.info("👋 提醒调度器已停止")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点，用于实时推送提醒"""
    await websocket_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        websocket_manager.disconnect(websocket)

# 注册路由
# 同时注册 /api 前缀版本（生产环境）和无前缀版本（开发环境兼容）
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(memories.router, prefix="/api", tags=["memory"])
app.include_router(reminders.router, prefix="/api", tags=["reminders"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])
app.include_router(tools.router, prefix="/api", tags=["tools"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(voice.router, prefix="/api", tags=["voice"])
app.include_router(schedule.router, prefix="/api", tags=["schedule"])
app.include_router(feedback.router, prefix="/api", tags=["feedback"])
app.include_router(faces.router, prefix="/api", tags=["faces"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(vision.router, prefix="/api", tags=["vision"])

# 同时注册无前缀版本（开发环境兼容）
app.include_router(auth.router, tags=["auth"])
app.include_router(chat.router, tags=["chat"])
app.include_router(memories.router, tags=["memory"])
app.include_router(reminders.router, tags=["reminders"])
app.include_router(tasks.router, tags=["tasks"])
app.include_router(tools.router, tags=["tools"])
app.include_router(analytics.router, tags=["analytics"])
app.include_router(documents.router, tags=["documents"])
app.include_router(voice.router, tags=["voice"])
app.include_router(schedule.router, tags=["schedule"])
app.include_router(feedback.router, tags=["feedback"])
app.include_router(faces.router, tags=["faces"])
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(vision.router, tags=["vision"])


@app.get("/health")
def health():
    """健康检查端点"""
    return {"status": "ok"}


@app.post("/think")
def think(prompt: str):
    agent = get_xiaole_agent()
    return {"result": agent.think(prompt)}


@app.post("/act")
def act(command: str):
    agent = get_xiaole_agent()
    return {"result": agent.act(command)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
