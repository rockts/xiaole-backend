"""
提醒工具 - v0.5.0
支持智能创建时间提醒
"""
from datetime import datetime, timedelta
import re
from tool_manager import Tool, ToolParameter


class ReminderTool(Tool):
    """提醒工具 - 创建、查询、删除提醒"""

    def __init__(self):
        super().__init__()
        self.name = "reminder"
        self.description = "提醒管理工具（创建、查询、删除）"
        self.category = "reminder"
        self.enabled = True
        self.parameters = [
            ToolParameter(
                name="operation",
                param_type="string",
                description="操作类型：create(创建), list(查询), delete(删除), update(修改)",
                required=False,
                default="create",
                enum=["create", "list", "delete", "update"]
            ),
            ToolParameter(
                name="content",
                param_type="string",
                description="提醒内容（创建时必填，修改时可选）",
                required=False
            ),
            ToolParameter(
                name="time_desc",
                param_type="string",
                description="时间描述（创建时必填，修改时可选，如：明天下午3点）",
                required=False
            ),
            ToolParameter(
                name="title",
                param_type="string",
                description="提醒标题（可选）",
                required=False
            ),
            ToolParameter(
                name="reminder_id",
                param_type="number",
                description="提醒ID（删除/修改时必填）",
                required=False
            ),
            ToolParameter(
                name="status",
                param_type="string",
                description="查询状态：active(未完成/默认), all(所有), completed(已完成)",
                required=False,
                default="active",
                enum=["active", "all", "completed"]
            )
        ]

    async def execute(self, **kwargs) -> dict:
        """
        执行提醒操作

        Args:
            **kwargs: 包含 operation, content, time_desc, title, reminder_id, user_id, status
        """
        try:
            operation = kwargs.get("operation", "create")
            user_id = kwargs.get("user_id", "default_user")

            from reminder_manager import get_reminder_manager
            reminder_mgr = get_reminder_manager()

            if operation == "list":
                return self._handle_list(reminder_mgr, user_id, kwargs)
            elif operation == "delete":
                return self._handle_delete(reminder_mgr, kwargs)
            elif operation == "update":
                return self._handle_update(reminder_mgr, kwargs)
            else:
                return self._handle_create(reminder_mgr, kwargs, user_id)

        except Exception as e:
            import logging
            logging.error(f"提醒操作失败: {e}")
            return {
                "success": False,
                "data": f"❌ 操作失败: {str(e)}"
            }

    def _handle_list(self, mgr, user_id: str, kwargs: dict) -> dict:
        """处理查询请求"""
        import logging
        logger = logging.getLogger(__name__)

        status = kwargs.get("status", "active")

        # 确定查询范围
        enabled_only = True
        if status == "all" or status == "completed":
            enabled_only = False

        logger.info(
            f"🔍 查询提醒: user_id={user_id}, status={status}, "
            f"enabled_only={enabled_only}"
        )
        reminders = mgr.get_user_reminders(
            user_id, enabled_only=enabled_only
        )
        logger.info(f"📋 查询结果: 找到 {len(reminders)} 条提醒")
        if reminders:
            details = [
                {
                    'id': r['reminder_id'],
                    'content': r['content'],
                    'enabled': r['enabled']
                }
                for r in reminders
            ]
            logger.info(f"📝 提醒详情: {details}")

        # 如果只查 completed，在内存中过滤
        if status == "completed":
            reminders = [r for r in reminders if not r['enabled']]

        if not reminders:
            # 如果查询 active 为空，尝试检查是否有 completed 的提醒，给用户更好的反馈
            if status == "active":
                all_reminders = mgr.get_user_reminders(
                    user_id, enabled_only=False
                )
                completed_reminders = [
                    r for r in all_reminders if not r['enabled']
                ]

                if completed_reminders:
                    # 按时间倒序
                    completed_reminders.sort(
                        key=lambda x: x['created_at'], reverse=True
                    )
                    recent = completed_reminders[:3]

                    lines = [
                        f"📭 你目前没有**未完成**的提醒，但有 "
                        f"{len(completed_reminders)} 条已完成/已禁用的提醒："
                    ]
                    for r in recent:
                        time_str = self._format_reminder_time(r)
                        lines.append(
                            f"- [已结束] {r['content']} (原定: {time_str})"
                        )

                    return {
                        "success": True,
                        "data": "\n".join(lines)
                    }

            return {
                "success": True,
                "data": "⚠️ 【最新查询结果】\n📭 提醒列表为空。"
            }

        # 格式化提醒列表
        status_text = "未完成"
        if status == "completed":
            status_text = "已完成"
        elif status == "all":
            status_text = "所有"

        lines = [
            "⚠️ 【最新查询结果 - 请忽略历史记录】",
            f"📋 **{status_text}提醒列表**（共{len(reminders)}条）："
        ]

        for r in reminders:
            time_str = self._format_reminder_time(r)

            state_icon = "⏰" if r['enabled'] else "✅"
            state_text = "" if r['enabled'] else "[已结束] "

            lines.append(
                f"- ID:{r['reminder_id']} | {state_icon} "
                f"{state_text}{time_str} | {r['content']}"
            )

        return {
            "success": True,
            "data": "\n".join(lines)
        }

    def _format_reminder_time(self, r: dict) -> str:
        """格式化单条提醒的时间"""
        trigger_cond = r.get('trigger_condition', {})
        if isinstance(trigger_cond, str):
            import json
            try:
                trigger_cond = json.loads(trigger_cond)
            except Exception:
                pass

        time_str = "未知时间"
        if r.get('reminder_type') == 'time':
            dt_str = trigger_cond.get('datetime', '')
            try:
                dt = datetime.fromisoformat(dt_str)
                time_str = self._format_time_display(dt)
            except Exception:
                time_str = dt_str
        return time_str

    def _handle_delete(self, mgr, kwargs) -> dict:
        """处理删除请求"""
        reminder_id = kwargs.get("reminder_id")
        if not reminder_id:
            return {"success": False, "data": "❌ 删除提醒需要提供 reminder_id"}

        success = mgr.delete_reminder(int(reminder_id))
        if success:
            return {"success": True, "data": f"✅ 提醒已删除 (ID: {reminder_id})"}
        else:
            return {
                "success": False,
                "data": f"❌ 删除失败，未找到提醒 ID: {reminder_id}"
            }

    def _handle_create(self, mgr, kwargs, user_id) -> dict:
        """处理创建请求"""
        content = kwargs.get("content", "")
        time_desc = kwargs.get("time_desc", "")
        title = kwargs.get("title") or self._extract_title(content)
        task_id = kwargs.get("task_id")

        if not content or not time_desc:
            return {
                "success": False,
                "data": "❌ 创建提醒需要提供内容(content)和时间(time_desc)"
            }

        # 解析时间描述，转换为具体时间
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🕐 开始解析时间: time_desc='{time_desc}'")
        trigger_time = self._parse_time(time_desc)
        logger.info(f"🕐 解析结果: {trigger_time}")

        if not trigger_time:
            return {
                "success": False,
                "data": (
                    f"❌ 无法识别时间：{time_desc}\n"
                    "支持格式：明天/后天/X小时后/X分钟后/具体时间"
                )
            }

        reminder = mgr.create_reminder(
            user_id=user_id,
            reminder_type="time",
            trigger_condition={
                "datetime": trigger_time.strftime("%Y-%m-%d %H:%M:%S")},
            content=content,
            title=title,
            priority=2,
            repeat=False,
            task_id=task_id
        )

        # 格式化时间显示
        time_str = self._format_time_display(trigger_time)

        return {
            "success": True,
            "data": f"✅ 提醒已创建：{title}\n⏰ 触发时间：{time_str}\n📝 内容：{content}",
            "reminder_id": reminder['reminder_id']
        }

    def _handle_update(self, mgr, kwargs) -> dict:
        """处理修改请求"""
        reminder_id = kwargs.get("reminder_id")
        user_id = kwargs.get("user_id", "default_user")

        # 智能ID推断：如果未提供ID，尝试查找唯一活跃提醒
        if not reminder_id:
            import logging
            logger = logging.getLogger(__name__)
            logger.info("🔍 修改提醒未提供ID，尝试智能查找唯一活跃提醒...")

            active_reminders = mgr.get_user_reminders(
                user_id, enabled_only=True
            )

            if len(active_reminders) == 1:
                reminder_id = active_reminders[0]['reminder_id']
                logger.info(f"✅ 智能锁定唯一提醒 ID: {reminder_id}")
            elif len(active_reminders) == 0:
                return {
                    "success": False,
                    "data": "❌ 当前没有未完成的提醒，无法修改。"
                }
            else:
                # 多个提醒，列出让用户选择
                lines = ["❌ 无法确定要修改哪个提醒，请提供ID："]
                for r in active_reminders:
                    time_str = self._format_reminder_time(r)
                    lines.append(
                        f"- ID:{r['reminder_id']} | {time_str} | {r['content']}")
                return {
                    "success": False,
                    "data": "\n".join(lines)
                }

        updates = {}

        # 处理内容更新
        content = kwargs.get("content")
        if content:
            updates["content"] = content
            # 如果更新了内容但没指定标题，尝试更新标题
            if not kwargs.get("title"):
                updates["title"] = self._extract_title(content)

        # 处理标题更新
        title = kwargs.get("title")
        if title:
            updates["title"] = title

        # 处理时间更新
        time_desc = kwargs.get("time_desc")
        if time_desc:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"🕐 开始解析新时间: time_desc='{time_desc}'")
            trigger_time = self._parse_time(time_desc)

            if not trigger_time:
                return {
                    "success": False,
                    "data": (
                        f"❌ 无法识别新时间：{time_desc}\n"
                        "支持格式：明天/后天/X小时后/X分钟后/具体时间"
                    )
                }

            updates["trigger_condition"] = {
                "datetime": trigger_time.strftime("%Y-%m-%d %H:%M:%S")
            }
            # 格式化时间显示用于返回消息
            time_str = self._format_time_display(trigger_time)
        else:
            time_str = "保持原时间"

        if not updates:
            return {"success": False, "data": "⚠️ 未提供任何需要修改的内容"}

        updated_reminder = mgr.update_reminder(int(reminder_id), **updates)

        if updated_reminder:
            msg_parts = [f"✅ 提醒已修改 (ID: {reminder_id})"]

            # 显示当前最新状态
            current_content = updated_reminder.get('content', '未知内容')
            msg_parts.append(f"📝 当前内容：{current_content}")

            # 格式化时间
            time_str = self._format_reminder_time(updated_reminder)
            msg_parts.append(f"⏰ 当前时间：{time_str}")

            return {"success": True, "data": "\n".join(msg_parts)}
        else:
            return {
                "success": False,
                "data": f"❌ 修改失败，未找到提醒 ID: {reminder_id}"
            }

    def _extract_title(self, content: str) -> str:
        """从内容中提取标题"""
        # 如果内容较短（30字以内），直接用内容做标题，实现“标题内容合一”
        if len(content) <= 30:
            return content

        # 如果内容较长，截取前20个字作为标题
        return content[:20] + "..."

    def _parse_time(self, time_desc: str) -> datetime:
        """
        解析时间描述，返回具体时间

        支持格式：
        - 明天/后天 + 时间（如：明天下午3点、后天早上9点）
        - X小时后/X分钟后
        - 具体时间（如：2025-11-11 15:00）
        """
        now = datetime.now()
        time_desc = time_desc.strip()

        # 1. 处理"X小时后" 或 "X小时"
        match = re.search(r'(\d+)\s*[个]?\s*小时(后)?', time_desc)
        if match:
            hours = int(match.group(1))
            return now + timedelta(hours=hours)

        # 2. 处理"X分钟后" 或 "X分钟"
        match = re.search(r'(\d+)\s*[个]?\s*分钟(后)?', time_desc)
        if match:
            minutes = int(match.group(1))
            return now + timedelta(minutes=minutes)

        # 2.5 处理"X秒后" 或 "X秒"
        match = re.search(r'(\d+)\s*秒(后)?', time_desc)
        if match:
            seconds = int(match.group(1))
            return now + timedelta(seconds=seconds)

        # 3. 处理"明天"
        if '明天' in time_desc or '明日' in time_desc:
            target_date = now + timedelta(days=1)
            time_part = self._extract_time_part(time_desc)
            if time_part:
                return target_date.replace(
                    hour=time_part['hour'],
                    minute=time_part.get('minute', 0),
                    second=0,
                    microsecond=0
                )
            else:
                # 默认明天上午9点
                return target_date.replace(
                    hour=9, minute=0, second=0, microsecond=0
                )

        # 4. 处理"后天"
        if '后天' in time_desc:
            target_date = now + timedelta(days=2)
            time_part = self._extract_time_part(time_desc)
            if time_part:
                return target_date.replace(
                    hour=time_part['hour'],
                    minute=time_part.get('minute', 0),
                    second=0,
                    microsecond=0
                )
            else:
                return target_date.replace(
                    hour=9, minute=0, second=0, microsecond=0
                )

        # 5. 处理"今天"
        if '今天' in time_desc or '今日' in time_desc:
            time_part = self._extract_time_part(time_desc)
            if time_part:
                return now.replace(
                    hour=time_part['hour'],
                    minute=time_part.get('minute', 0),
                    second=0,
                    microsecond=0
                )

        # 6. 处理具体时间格式：YYYY-MM-DD HH:MM
        try:
            return datetime.strptime(time_desc, "%Y-%m-%d %H:%M")
        except ValueError:
            pass

        # 7. 处理相对时间（如：下午3点、晚上8点）
        time_part = self._extract_time_part(time_desc)
        if time_part:
            target = now.replace(
                hour=time_part['hour'],
                minute=time_part.get('minute', 0),
                second=0,
                microsecond=0
            )
            # 如果时间已过，设置为明天
            if target <= now:
                target += timedelta(days=1)
            return target

        return None

    def _extract_time_part(self, text: str) -> dict:
        """
        从文本中提取时间部分
        返回: {"hour": int, "minute": int} 或 None
        """
        # 匹配 "下午3点"、"晚上8点"、"早上9点"
        match = re.search(r'(早上|上午|中午|下午|晚上|凌晨)?(\d{1,2})点(\d{1,2}分)?', text)
        if match:
            period = match.group(1) or ""
            hour = int(match.group(2))
            minute_str = match.group(3)
            minute = int(minute_str[:-1]) if minute_str else 0

            # 调整小时（12小时制转24小时制）
            if period in ['下午', '晚上'] and hour < 12:
                hour += 12
            elif period == '凌晨' and hour == 12:
                hour = 0

            return {"hour": hour, "minute": minute}

        # 匹配 "15:30"、"3:00"
        match = re.search(r'(\d{1,2}):(\d{2})', text)
        if match:
            return {
                "hour": int(match.group(1)),
                "minute": int(match.group(2))
            }

        return None

    def _format_time_display(self, dt: datetime) -> str:
        """格式化时间显示"""
        now = datetime.now()
        delta = dt - now

        if delta.days == 0:
            if delta.seconds < 60:
                return f"今天 {dt.strftime('%H:%M:%S')} ({delta.seconds}秒后)"
            elif delta.seconds < 3600:
                minutes = delta.seconds // 60
                return f"今天 {dt.strftime('%H:%M')} ({minutes}分钟后)"
            else:
                hours = delta.seconds // 3600
                return f"今天 {dt.strftime('%H:%M')} ({hours}小时后)"
        elif delta.days == 1:
            return f"明天 {dt.strftime('%H:%M')}"
        elif delta.days == 2:
            return f"后天 {dt.strftime('%H:%M')}"
        else:
            return dt.strftime("%Y-%m-%d %H:%M")
