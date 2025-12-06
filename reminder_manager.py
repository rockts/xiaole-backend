"""
主动提醒系统
支持时间、天气、行为、习惯等多种触发类型
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import logging

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    """获取数据库连接"""
    host = os.getenv('DB_HOST')
    port = os.getenv('DB_PORT', '5432')
    dbname = os.getenv('DB_NAME')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASS')

    if not all([host, dbname, user, password]):
        raise ValueError(
            "Database configuration is missing. Please check environment variables.")

    conn = psycopg2.connect(
        host=host,
        port=port,
        database=dbname,
        user=user,
        password=password,
        client_encoding='UTF8'
    )
    return conn


logger = logging.getLogger(__name__)


class ReminderType:
    """提醒类型常量"""
    TIME = "time"           # 时间提醒（生日、纪念日、定时任务）
    WEATHER = "weather"     # 天气提醒（下雨带伞、温度变化）
    BEHAVIOR = "behavior"   # 行为提醒（长时间未聊天）
    HABIT = "habit"         # 习惯提醒（基于行为模式）


class ReminderStatus:
    """提醒状态"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    TRIGGERED = "triggered"
    EXPIRED = "expired"


class ReminderManager:
    """
    主动提醒管理器
    功能：
    1. 创建、查询、更新、删除提醒
    2. 检查触发条件
    3. 发送提醒通知
    4. 记录提醒历史
    """

    def __init__(self, websocket_broadcast_callback=None):
        self.reminders_cache: Dict[str, List[Dict]] = {}  # 用户提醒缓存
        self.last_cache_update = None
        self.cache_ttl = 300  # 缓存5分钟
        self.websocket_broadcast = websocket_broadcast_callback  # WebSocket推送回调
        self._loop = None

    def set_loop(self, loop):
        self._loop = loop

    def _broadcast(self, message):
        if self.websocket_broadcast and self._loop:
            asyncio.run_coroutine_threadsafe(
                self.websocket_broadcast(message),
                self._loop
            )

    def create_reminder(
        self,
        user_id: str,
        reminder_type: str,
        trigger_condition: Dict[str, Any],
        content: str,
        title: Optional[str] = None,
        priority: int = 1,
        repeat: bool = False,
        repeat_interval: Optional[int] = None,  # 秒
        task_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        创建提醒

        Args:
            user_id: 用户ID
            reminder_type: 提醒类型（time/weather/behavior/habit）
            trigger_condition: 触发条件JSON
                time类型: {"datetime": "2025-12-25 10:00:00"}
                weather类型: {"condition": "rain", "location": "天水"}
                behavior类型: {"inactive_hours": 24}
                habit类型: {"pattern": "morning_greeting", "time": "08:00"}
            content: 提醒内容
            title: 提醒标题
            priority: 优先级（1-5，1最高）
            repeat: 是否重复
            repeat_interval: 重复间隔（秒）
            task_id: 关联的任务ID

        Returns:
            创建的提醒信息
        """
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO reminders (
                        user_id, reminder_type, trigger_condition,
                        content, title, priority, repeat, repeat_interval,
                        enabled, created_at, task_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                    RETURNING reminder_id, user_id, reminder_type, trigger_condition,
                              content, title, priority, repeat, repeat_interval,
                              enabled, created_at, task_id
                """, (
                    user_id, reminder_type, json.dumps(trigger_condition),
                    content, title, priority, repeat, repeat_interval, True, task_id
                ))
                reminder = dict(cur.fetchone())
                conn.commit()

                # 清除缓存
                self._clear_user_cache(user_id)

                logger.info(
                    f"Created reminder {reminder['reminder_id']} for user {user_id}")

                # 保存到记忆系统
                try:
                    from memory import MemoryManager
                    memory_mgr = MemoryManager()

                    # 构建记忆内容
                    trigger_str = ""
                    if reminder_type == "time":
                        trigger_cond = trigger_condition if isinstance(
                            trigger_condition, dict) else json.loads(trigger_condition)
                        trigger_str = f"时间: {trigger_cond.get('datetime', '未知')}"

                    memory_content = f"用户创建了提醒「{title or content[:20]}」\n内容: {content}\n{trigger_str}"
                    memory_mgr.remember(
                        content=memory_content,
                        tag="reminder"
                    )
                    logger.info(f"💾 提醒已保存到记忆系统")
                except Exception as mem_error:
                    logger.warning(f"保存提醒记忆失败: {mem_error}")

                # 广播提醒创建事件，以便前端刷新列表
                if self.websocket_broadcast:
                    try:
                        # 转换datetime对象为字符串，避免JSON序列化错误
                        reminder_data = reminder.copy()
                        if 'created_at' in reminder_data and reminder_data['created_at']:
                            reminder_data['created_at'] = reminder_data['created_at'].isoformat(
                            )

                        self._broadcast({
                            "type": "reminder_created",
                            "data": reminder_data
                        })
                    except Exception as ws_error:
                        logger.error(f"WebSocket broadcast failed: {ws_error}")

                return reminder

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create reminder: {e}")
            raise
        finally:
            conn.close()

    def get_user_reminders(
        self,
        user_id: str,
        enabled_only: bool = True,
        reminder_type: Optional[str] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取用户的提醒列表

        Args:
            user_id: 用户ID
            enabled_only: 是否只返回启用的提醒
            reminder_type: 提醒类型过滤
            use_cache: 是否使用缓存

        Returns:
            提醒列表
        """
        # 检查缓存
        cache_key = f"{user_id}_{enabled_only}_{reminder_type}"
        if use_cache and self._is_cache_valid() and cache_key in self.reminders_cache:
            return self.reminders_cache[cache_key]

        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = "SELECT * FROM reminders WHERE user_id = %s"
                params = [user_id]

                if enabled_only:
                    query += " AND enabled = true"

                if reminder_type:
                    query += " AND reminder_type = %s"
                    params.append(reminder_type)

                # 优化排序：启用的在前，然后按优先级（小号优先），最后按创建时间倒序
                query += (
                    " ORDER BY enabled DESC, priority ASC, created_at DESC"
                )

                cur.execute(query, params)
                reminders = [dict(row) for row in cur.fetchall()]

                # 更新缓存
                self.reminders_cache[cache_key] = reminders
                self.last_cache_update = datetime.now()

                return reminders

        except Exception as e:
            logger.error(f"Failed to get user reminders: {e}")
            return []
        finally:
            conn.close()

    def update_reminder(
        self,
        reminder_id: int,
        **updates
    ) -> Optional[Dict[str, Any]]:
        """
        更新提醒

        Args:
            reminder_id: 提醒ID
            **updates: 要更新的字段

        Returns:
            更新后的提醒信息（如果成功），否则为None
        """
        if not updates:
            return None

        # 处理JSONB字段：将字典转为JSON字符串
        processed_updates = {}
        for key, value in updates.items():
            if isinstance(value, dict):
                processed_updates[key] = json.dumps(value)
            else:
                processed_updates[key] = value

        # 构建更新SQL
        set_clause = ", ".join([f"{k} = %s" for k in processed_updates.keys()])
        values = list(processed_updates.values())
        values.append(reminder_id)

        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"""
                    UPDATE reminders
                    SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                    WHERE reminder_id = %s
                    RETURNING *
                """, values)
                updated_reminder = cur.fetchone()
                conn.commit()

                if updated_reminder:
                    updated_reminder = dict(updated_reminder)
                    # 清除所有缓存
                    self.reminders_cache.clear()

                    logger.info(f"Updated reminder {reminder_id}")

                    # 广播提醒更新事件
                    if self.websocket_broadcast:
                        try:
                            self._broadcast({
                                "type": "reminder_updated",
                                "data": {
                                    "reminder_id": reminder_id,
                                    "updates": updates
                                }
                            })
                        except Exception as ws_error:
                            logger.error(
                                f"WebSocket broadcast failed: {ws_error}")

                    return updated_reminder
                else:
                    return None

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update reminder: {e}")
            return None
        finally:
            conn.close()

    def delete_reminder(self, reminder_id: int) -> bool:
        """删除提醒"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # 先查询用户ID，以便清除缓存
                cur.execute(
                    "SELECT user_id FROM reminders WHERE reminder_id = %s",
                    (reminder_id,)
                )
                result = cur.fetchone()
                user_id = result[0] if result else None

                cur.execute(
                    "DELETE FROM reminders WHERE reminder_id = %s", (reminder_id,))
                conn.commit()

                # 清除缓存
                self.reminders_cache.clear()

                logger.info(f"Deleted reminder {reminder_id}")

                # 广播删除事件
                if self.websocket_broadcast:
                    try:
                        self._broadcast({
                            "type": "reminder_deleted",
                            "data": {
                                "reminder_id": reminder_id
                            }
                        })
                    except Exception as ws_error:
                        logger.error(f"WebSocket broadcast failed: {ws_error}")

                return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete reminder: {e}")
            return False
        finally:
            conn.close()

    def check_time_reminders(self, user_id: str) -> List[Dict[str, Any]]:
        """
        检查时间类型的提醒

        Returns:
            需要触发的提醒列表
        """
        # 强制不使用缓存，确保获取最新的数据库状态（特别是Snooze更新后）
        reminders = self.get_user_reminders(
            user_id,
            enabled_only=True,
            reminder_type=ReminderType.TIME,
            use_cache=False
        )

        triggered = []
        now = datetime.now()

        for reminder in reminders:
            try:
                condition = reminder['trigger_condition']
                if isinstance(condition, str):
                    condition = json.loads(condition)

                # 解析触发时间
                trigger_time_str = condition.get('datetime')
                if not trigger_time_str:
                    continue

                # 兼容多种时间格式
                try:
                    # 尝试 ISO 8601 格式(带时区)
                    trigger_time = datetime.fromisoformat(trigger_time_str)
                    # 如果带时区,转为本地时区并去除时区信息(与 now 统一为 naive datetime)
                    if trigger_time.tzinfo is not None:
                        trigger_time = trigger_time.astimezone().replace(tzinfo=None)
                except ValueError:
                    # 尝试简单格式 "YYYY-MM-DD HH:MM:SS"
                    trigger_time = datetime.strptime(
                        trigger_time_str, "%Y-%m-%d %H:%M:%S")

                # DEBUG: 打印检查信息
                logger.info(
                    f"Checking reminder {reminder['reminder_id']}: trigger={trigger_time}, now={now}")

                # 检查是否到时间
                if now >= trigger_time:
                    # 检查是否最近已触发（避免重复）
                    last_triggered = reminder.get('last_triggered')
                    if last_triggered:
                        # 如果刚刚触发过（10秒内），忽略（防止并发重复触发）
                        if (now - last_triggered).total_seconds() < 10:
                            continue

                        # 如果是重复提醒，检查间隔
                        if reminder.get('repeat'):
                            interval = reminder.get(
                                'repeat_interval', 86400)  # 默认1天
                            if (now - last_triggered).total_seconds() < interval:
                                continue
                        else:
                            # 非重复提醒，如果已启用（未确认），每5分钟提醒一次
                            # 只有当当前时间超过触发时间很久了（比如错过了），才需要这个重试逻辑
                            # 如果是Snooze的情况，trigger_time应该是未来的时间，now < trigger_time，根本进不来这里
                            # 所以这里的逻辑只针对：trigger_time已过，但用户没确认的情况

                            retry_interval = 300  # 5分钟
                            time_since_last = (
                                now - last_triggered).total_seconds()

                            # 如果距离上次触发还不到5分钟，跳过
                            if time_since_last < retry_interval:
                                continue

                            # 只有当 trigger_time 确实是过去的时间时，才执行重试
                            # (虽然外层 if now >= trigger_time 已经保证了这点)

                    triggered.append(reminder)
                    logger.info(
                        f"Reminder {reminder['reminder_id']} triggered! Time: {trigger_time}, Now: {now}")

            except Exception as e:
                logger.error(
                    f"Failed to check time reminder {reminder['reminder_id']}: {e}")

        return triggered

    def check_behavior_reminders(self, user_id: str) -> List[Dict[str, Any]]:
        """
        检查行为类型的提醒（如长时间未聊天）

        Returns:
            需要触发的提醒列表
        """
        # 强制不使用缓存
        reminders = self.get_user_reminders(
            user_id,
            enabled_only=True,
            reminder_type=ReminderType.BEHAVIOR,
            use_cache=False
        )

        triggered = []

        # 获取用户最后活跃时间
        last_active = self._get_user_last_active(user_id)
        if not last_active:
            return triggered

        now = datetime.now()
        inactive_hours = (now - last_active).total_seconds() / 3600

        for reminder in reminders:
            try:
                condition = reminder['trigger_condition']
                if isinstance(condition, str):
                    condition = json.loads(condition)

                # 检查是否有稍后提醒的设定时间
                snooze_until_str = condition.get('datetime')
                if snooze_until_str:
                    snooze_until = datetime.fromisoformat(snooze_until_str)
                    if now < snooze_until:
                        continue

                # 检查不活跃时间
                required_hours = condition.get('inactive_hours', 24)
                if inactive_hours >= required_hours:
                    # 检查是否最近已触发
                    last_triggered = reminder.get('last_triggered')
                    if last_triggered:
                        hours_since_last = (
                            now - last_triggered).total_seconds() / 3600
                        if hours_since_last < required_hours:
                            continue

                    triggered.append(reminder)

            except Exception as e:
                logger.error(
                    f"Failed to check behavior reminder {reminder['reminder_id']}: {e}")

        return triggered

    def check_and_notify_reminder(self, reminder_id: int) -> bool:
        """
        检查提醒并通过WebSocket推送通知（不写入历史）

        Args:
            reminder_id: 提醒ID

        Returns:
            是否成功推送
        """
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 获取提醒信息
                cur.execute("""
                    SELECT * FROM reminders WHERE reminder_id = %s
                """, (reminder_id,))
                reminder = cur.fetchone()

                if not reminder:
                    logger.error(f"Reminder {reminder_id} not found")
                    return False

                reminder = dict(reminder)

                # 更新last_triggered（标记为已通知但未确认）
                cur.execute("""
                    UPDATE reminders
                    SET last_triggered = CURRENT_TIMESTAMP,
                        trigger_count = COALESCE(trigger_count, 0) + 1
                    WHERE reminder_id = %s
                """, (reminder_id,))

                conn.commit()

                # 清除缓存，确保下次检查时能获取到最新的last_triggered
                self._clear_user_cache(reminder['user_id'])

                logger.info(
                    f"Notified reminder {reminder_id} (not confirmed yet)"
                )

                # 动态生成语音提醒内容
                trigger_count = reminder.get('trigger_count', 0) + 1
                # 尝试获取用户昵称，这里暂时使用默认值，后续可以从用户配置中获取
                nickname = "主人"

                # 格式化时间
                current_time_str = datetime.now().strftime("%H:%M")

                voice_text = ""
                content = reminder['content']

                if trigger_count <= 1:
                    # 第一次提醒
                    voice_text = f"现在是{current_time_str}，请{nickname}{content}。"
                elif trigger_count == 2:
                    # 第二次提醒（稍后提醒后）
                    voice_text = f"请{nickname}赶快{content}。"
                else:
                    # 第三次及以上
                    voice_text = f"请{nickname}立马马上{content}！"

                # WebSocket实时推送提醒（用户需要确认）
                if self.websocket_broadcast:
                    try:
                        self._broadcast({
                            "type": "reminder",
                            "data": {
                                "reminder_id": reminder_id,
                                "title": reminder.get('title', '提醒'),
                                "content": reminder['content'],
                                "voice_text": voice_text,  # 新增字段
                                "priority": reminder.get('priority', 3),
                                "reminder_type": reminder.get('reminder_type'),
                                "triggered_at": datetime.now().isoformat()
                            }
                        })
                        logger.info(f"WebSocket推送提醒 {reminder_id}")
                        return True
                    except Exception as ws_error:
                        logger.error(f"WebSocket推送失败: {ws_error}")
                        return False
                else:
                    logger.warning("No WebSocket broadcast callback available")
                    return False

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to notify reminder: {e}")
            return False
        finally:
            conn.close()

    def snooze_reminder(self, reminder_id: int, minutes: int = 5) -> bool:
        """
        延迟提醒（稍后提醒）
        """
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 获取当前提醒
                cur.execute(
                    "SELECT * FROM reminders WHERE reminder_id = %s",
                    (reminder_id,)
                )
                reminder = cur.fetchone()

                if not reminder:
                    return False

                # 计算新的触发时间
                new_trigger_time = datetime.now() + timedelta(minutes=minutes)
                new_time_str = new_trigger_time.strftime('%Y-%m-%d %H:%M:%S')

                # 更新trigger_condition
                raw_condition = reminder['trigger_condition']
                if isinstance(raw_condition, str):
                    trigger_condition = json.loads(raw_condition)
                elif isinstance(raw_condition, dict):
                    trigger_condition = raw_condition.copy()
                else:
                    trigger_condition = {}

                trigger_condition['datetime'] = new_time_str
                trigger_condition_json = json.dumps(trigger_condition)

                cur.execute("""
                    UPDATE reminders
                    SET trigger_condition = %s,
                        last_triggered = NULL,
                        enabled = true,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE reminder_id = %s
                """, (trigger_condition_json, reminder_id))

                conn.commit()

                if cur.rowcount > 0:
                    self._clear_user_cache(reminder['user_id'])
                    logger.info(
                        f"Snoozed reminder {reminder_id} for {minutes} mins"
                    )
                    return True
                return False

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to snooze reminder: {e}")
            return False
        finally:
            conn.close()

    def confirm_reminder(self, reminder_id: int) -> bool:
        """
        用户确认提醒（点击"已知道"），记录历史并禁用

        Args:
            reminder_id: 提醒ID

        Returns:
            是否成功
        """
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 获取提醒信息
                cur.execute("""
                    SELECT * FROM reminders WHERE reminder_id = %s
                """, (reminder_id,))
                reminder = cur.fetchone()

                if not reminder:
                    logger.error(f"Reminder {reminder_id} not found")
                    return False

                reminder = dict(reminder)
                logger.info(
                    f"Confirming reminder {reminder_id}, "
                    f"repeat={reminder.get('repeat')}"
                )

                # 记录提醒历史（用户已确认）
                cur.execute("""
                    INSERT INTO reminder_history (
                        reminder_id, user_id, content, triggered_at
                    ) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    reminder_id,
                    reminder['user_id'],
                    reminder['content']
                ))

                # 如果是非重复提醒，禁用它
                # 确保正确处理 None 或 0 的情况
                is_repeat = reminder.get('repeat')
                repeat_interval = reminder.get('repeat_interval')

                # 如果标记为重复，但没有设置间隔，视为非重复（防御性编程）
                if is_repeat and (not repeat_interval or repeat_interval <= 0):
                    logger.warning(
                        f"Reminder {reminder_id} marked as repeat but has "
                        f"invalid interval {repeat_interval}. "
                        f"Treating as non-repeat."
                    )
                    is_repeat = False

                if not is_repeat:
                    logger.info(
                        f"Disabling non-repeating reminder {reminder_id}"
                    )
                    cur.execute("""
                        UPDATE reminders
                        SET enabled = false
                        WHERE reminder_id = %s
                    """, (reminder_id,))

                    # 既然状态改变了，需要清除缓存
                    self._clear_user_cache(reminder['user_id'])

                    # 广播更新事件
                    if self.websocket_broadcast:
                        try:
                            self._broadcast({
                                "type": "reminder_updated",
                                "data": {
                                    "reminder_id": reminder_id,
                                    "updates": {"enabled": False}
                                }
                            })
                        except Exception as ws_error:
                            logger.error(
                                f"WebSocket broadcast failed: {ws_error}")
                else:
                    logger.info(
                        f"Keeping repeating reminder {reminder_id} enabled"
                    )
                    # 对于重复提醒，重置trigger_count，以便下次触发时重新开始计数
                    cur.execute("""
                        UPDATE reminders
                        SET trigger_count = 0
                        WHERE reminder_id = %s
                    """, (reminder_id,))

                    # 对于重复提醒，我们也清除缓存，以防万一
                    self._clear_user_cache(reminder['user_id'])

                conn.commit()

                logger.info(
                    f"Confirmed reminder {reminder_id} (written to history)"
                )

                # 广播确认事件，通知前端关闭弹窗（解决多端/多标签页同步问题）
                if self.websocket_broadcast:
                    try:
                        self._broadcast({
                            "type": "reminder_confirmed",
                            "data": {
                                "reminder_id": reminder_id
                            }
                        })
                    except Exception as ws_error:
                        logger.error(f"WebSocket broadcast failed: {ws_error}")

                return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to confirm reminder: {e}")
            return False
        finally:
            conn.close()

    def get_reminder_history(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取提醒历史"""
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT h.*, r.title, r.reminder_type
                    FROM reminder_history h
                    LEFT JOIN reminders r ON h.reminder_id = r.reminder_id
                    WHERE h.user_id = %s
                    ORDER BY h.triggered_at DESC
                    LIMIT %s
                """, (user_id, limit))
                return [dict(row) for row in cur.fetchall()]

        except Exception as e:
            logger.error(f"Failed to get reminder history: {e}")
            return []
        finally:
            conn.close()

    def get_pending_reminders(
        self, user_id: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        获取待处理的提醒（已触发但未确认）
        """
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 查找已触发且未确认的提醒
                # 确认的标志是：reminder_history 中存在
                # triggered_at >= reminders.last_triggered 的记录
                cur.execute("""
                    SELECT r.*
                    FROM reminders r
                    WHERE r.user_id = %s
                    AND r.enabled = true
                    AND r.last_triggered IS NOT NULL
                    AND r.last_triggered > NOW() - INTERVAL '24 hours'
                    AND NOT EXISTS (
                        SELECT 1 FROM reminder_history h
                        WHERE h.reminder_id = r.reminder_id
                        AND h.triggered_at >= r.last_triggered
                    )
                    ORDER BY r.last_triggered DESC
                    LIMIT %s
                """, (user_id, limit))
                reminders = cur.fetchall()
                return [dict(r) for r in reminders]
        finally:
            conn.close()

    def _clear_user_cache(self, user_id: str):
        """清除用户相关的缓存"""
        keys_to_remove = [
            k for k in self.reminders_cache.keys() if k.startswith(user_id)]
        for key in keys_to_remove:
            self.reminders_cache.pop(key, None)

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self.last_cache_update:
            return False
        delta = datetime.now() - self.last_cache_update
        return delta.total_seconds() < self.cache_ttl

    def _get_user_last_active(self, user_id: str) -> Optional[datetime]:
        """获取用户最后活跃时间"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT MAX(m.created_at) as last_active
                    FROM messages m
                    JOIN conversations c ON m.session_id = c.session_id
                    WHERE c.user_id = %s AND m.role = 'user'
                """, (user_id,))
                result = cur.fetchone()
                return result[0] if result and result[0] else None

        except Exception as e:
            logger.error(f"Failed to get user last active: {e}")
            return None
        finally:
            conn.close()


# 全局单例
_reminder_manager = None


def get_reminder_manager(
    websocket_broadcast_callback=None
) -> ReminderManager:
    """获取提醒管理器单例"""
    global _reminder_manager
    if _reminder_manager is None:
        _reminder_manager = ReminderManager(websocket_broadcast_callback)
    elif websocket_broadcast_callback is not None:
        # 更新WebSocket回调
        _reminder_manager.websocket_broadcast = websocket_broadcast_callback
    return _reminder_manager
