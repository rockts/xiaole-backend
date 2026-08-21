from fastapi import APIRouter, Depends
from typing import Dict, Any
from dependencies import (
    get_xiaole_agent, get_task_manager
)
from agent import XiaoLeAgent
from modules.task_manager import TaskManager
from auth import get_current_user
import psutil
import os

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"]
)


def get_agent():
    return get_xiaole_agent()


def get_tasks():
    return get_task_manager()


@router.get("/snapshot")
def get_dashboard_snapshot(
    current_user: str = Depends(get_current_user),
    agent: XiaoLeAgent = Depends(get_agent),
    task_mgr: TaskManager = Depends(get_tasks)
):
    """获取仪表盘快照数据"""
    user_id = current_user
    try:
        # 1. 获取系统状态
        system_status = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }

        # 2. 获取任务统计
        task_stats = task_mgr.get_task_statistics(user_id)

        # 3. 获取最近会话
        recent_sessions = agent.conversation.get_recent_sessions(
            user_id, limit=5)

        return {
            "success": True,
            "system": system_status,
            "tasks": task_stats,
            "recent_sessions": recent_sessions,
            "agent_status": "online"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
