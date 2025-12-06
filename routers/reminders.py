from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from reminder_manager import get_reminder_manager, ReminderManager
from dependencies import get_scheduler
from scheduler import ReminderScheduler
from logger import logger
from auth import get_current_user

router = APIRouter(
    prefix="/reminders",
    tags=["reminders"]
)


class ReminderCreate(BaseModel):
    user_id: str = "default_user"
    reminder_type: str = "time"
    trigger_condition: Dict[str, Any]
    content: str
    title: Optional[str] = None
    priority: int = 3
    repeat: bool = False
    repeat_interval: Optional[int] = None


class ReminderUpdate(BaseModel):
    content: Optional[str] = None
    title: Optional[str] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None
    trigger_condition: Optional[Dict[str, Any]] = None


def get_manager():
    return get_reminder_manager()


def get_sched():
    return get_scheduler()


@router.post("", response_model=Dict[str, Any])
async def create_reminder(
    reminder: ReminderCreate,
    manager: ReminderManager = Depends(get_manager)
):
    """创建新提醒"""
    try:
        result = manager.create_reminder(
            user_id=reminder.user_id,
            reminder_type=reminder.reminder_type,
            trigger_condition=reminder.trigger_condition,
            content=reminder.content,
            title=reminder.title,
            priority=reminder.priority,
            repeat=reminder.repeat,
            repeat_interval=reminder.repeat_interval
        )
        return {
            "success": True,
            "reminder": result
        }
    except Exception as e:
        logger.error(f"创建提醒失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=Dict[str, Any])
async def get_reminders(
    enabled_only: bool = True,
    reminder_type: Optional[str] = None,
    current_user: str = Depends(get_current_user),
    manager: ReminderManager = Depends(get_manager)
):
    """获取用户提醒列表"""
    logger.info(
        f"📋 获取提醒列表 - user_id: {current_user}, enabled_only: {enabled_only}")
    reminders = manager.get_user_reminders(
        user_id=current_user,
        enabled_only=enabled_only,
        reminder_type=reminder_type
    )
    logger.info(f"📋 返回 {len(reminders)} 条提醒")
    return {
        "total": len(reminders),
        "reminders": reminders
    }


@router.get("/{reminder_id}", response_model=Dict[str, Any])
async def get_reminder(
    reminder_id: int,
    user_id: str = "default_user",
    manager: ReminderManager = Depends(get_manager)
):
    """获取单个提醒详情"""
    reminders = manager.get_user_reminders(user_id)
    reminder = next(
        (r for r in reminders if r['reminder_id'] == reminder_id), None)

    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    return reminder


@router.put("/{reminder_id}", response_model=Dict[str, Any])
async def update_reminder(
    reminder_id: int,
    reminder: ReminderUpdate,
    manager: ReminderManager = Depends(get_manager)
):
    """更新提醒"""
    updates = reminder.dict(exclude_unset=True)

    if 'trigger_condition' in updates:
        import json
        updates['trigger_condition'] = json.dumps(updates['trigger_condition'])

    success = manager.update_reminder(reminder_id, **updates)

    return {
        "success": bool(success),
        "message": "Reminder updated" if success else "Update failed"
    }


@router.delete("/{reminder_id}", response_model=Dict[str, Any])
async def delete_reminder(
    reminder_id: int,
    manager: ReminderManager = Depends(get_manager)
):
    """删除提醒"""
    success = manager.delete_reminder(reminder_id)
    return {
        "success": success,
        "message": "Reminder deleted" if success else "Delete failed"
    }


@router.post("/{reminder_id}/toggle", response_model=Dict[str, Any])
async def toggle_reminder(
    reminder_id: int,
    user_id: str = "default_user",
    manager: ReminderManager = Depends(get_manager)
):
    """启用/禁用提醒"""
    reminders = manager.get_user_reminders(
        user_id,
        enabled_only=False
    )
    reminder = next(
        (r for r in reminders if r['reminder_id'] == reminder_id), None
    )

    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    new_enabled = not reminder.get('enabled', True)
    success = manager.update_reminder(
        reminder_id,
        enabled=new_enabled
    )

    return {
        "success": bool(success),
        "enabled": new_enabled,
        "message": f"Reminder {'enabled' if new_enabled else 'disabled'}"
    }


@router.post("/{reminder_id}/trigger", response_model=Dict[str, Any])
async def trigger_reminder_manually(
    reminder_id: int,
    manager: ReminderManager = Depends(get_manager)
):
    """手动触发提醒（测试用）"""
    success = manager.check_and_notify_reminder(reminder_id)
    return {
        "success": success,
        "message": "Reminder notified" if success else "Notify failed"
    }


@router.post("/{reminder_id}/snooze", response_model=Dict[str, Any])
async def snooze_reminder(
    reminder_id: int,
    minutes: int = 5,
    manager: ReminderManager = Depends(get_manager)
):
    """延迟提醒（稍后提醒）"""
    success = manager.snooze_reminder(reminder_id, minutes)
    return {
        "success": success,
        "message": f"Reminder snoozed for {minutes} minutes" if success else "Snooze failed"
    }


@router.post("/{reminder_id}/confirm", response_model=Dict[str, Any])
async def confirm_reminder(
    reminder_id: int,
    manager: ReminderManager = Depends(get_manager)
):
    """用户确认提醒"""
    success = manager.confirm_reminder(reminder_id)
    return {
        "success": success,
        "message": "Reminder confirmed" if success else "Confirm failed"
    }


@router.get("/history/{user_id}", response_model=Dict[str, Any])
async def get_reminder_history(
    user_id: str,
    limit: int = 50,
    manager: ReminderManager = Depends(get_manager)
):
    """获取提醒历史"""
    history = manager.get_reminder_history(user_id, limit)
    return {
        "total": len(history),
        "history": history
    }


@router.post("/check", response_model=Dict[str, Any])
async def check_reminders(
    user_id: str = "default_user",
    manager: ReminderManager = Depends(get_manager)
):
    """手动检查并触发提醒"""
    time_triggered = manager.check_time_reminders(user_id)
    behavior_triggered = manager.check_behavior_reminders(user_id)
    all_triggered = time_triggered + behavior_triggered

    results = []
    for reminder in all_triggered:
        success = manager.check_and_notify_reminder(
            reminder['reminder_id']
        )
        results.append({
            "reminder_id": reminder['reminder_id'],
            "title": reminder.get('title', 'Untitled'),
            "content": reminder['content'],
            "notified": success
        })

    return {
        "total_checked": len(all_triggered),
        "triggered": results
    }


@router.get("/scheduler/status", response_model=Dict[str, Any])
def get_scheduler_status(
    scheduler: ReminderScheduler = Depends(get_sched)
):
    """获取调度器状态"""
    return scheduler.get_status()


@router.post("/scheduler/start", response_model=Dict[str, Any])
def start_scheduler(
    scheduler: ReminderScheduler = Depends(get_sched)
):
    """启动调度器"""
    scheduler.start()
    return {"message": "Scheduler started", "status": scheduler.get_status()}


@router.post("/scheduler/stop", response_model=Dict[str, Any])
def stop_scheduler(
    scheduler: ReminderScheduler = Depends(get_sched)
):
    """停止调度器"""
    scheduler.stop()
    return {"message": "Scheduler stopped", "status": scheduler.get_status()}
