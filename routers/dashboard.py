from fastapi import APIRouter, Depends
from typing import Dict, Any
from backend.dependencies import (
    get_xiaole_agent, get_reminder_manager, get_task_manager
)
from backend.agent import XiaoLeAgent
from backend.reminder_manager import ReminderManager
from backend.task_manager import TaskManager
from backend.auth import get_current_user
import psutil
import os

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"]
)


def get_agent():
    return get_xiaole_agent()


def get_reminders():
    return get_reminder_manager()


def get_tasks():
    return get_task_manager()


@router.get("/snapshot")
def get_dashboard_snapshot(
    current_user: str = Depends(get_current_user),
    agent: XiaoLeAgent = Depends(get_agent),
    reminder_mgr: ReminderManager = Depends(get_reminders),
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

        # 2. 获取提醒概览
        reminders = reminder_mgr.get_user_reminders(user_id, enabled_only=True)

        # 3. 获取任务统计
        task_stats = task_mgr.get_task_statistics(user_id)

        # 4. 获取最近会话
        recent_sessions = agent.conversation.get_recent_sessions(
            user_id, limit=5)

        return {
            "success": True,
            "system": system_status,
            "reminders": {
                "count": len(reminders),
                "items": reminders[:5]
            },
            "tasks": task_stats,
            "recent_sessions": recent_sessions,
            "agent_status": "online"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
