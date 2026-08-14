from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .errors import ReminderUnavailable
from .schemas import ReminderCreateCommand, ReminderResult


SHANGHAI = ZoneInfo("Asia/Shanghai")


class ReminderOutcome:
    def __init__(self, answer: str):
        self.answer = answer


class ReminderOrchestrator:
    def __init__(self, gateway):
        self.gateway = gateway

    def handle(self, message: str, history: list[dict], conversation_id: str, request_id: str, now: datetime | None = None) -> ReminderOutcome:
        try:
            return self._handle(message.strip(), history, conversation_id, request_id, now or datetime.now(SHANGHAI))
        except ReminderUnavailable:
            return ReminderOutcome("提醒服务暂时不可用，请稍后再试。")

    def _handle(self, text, history, conversation_id, request_id, now):
        reminder_id = self._explicit_id(text)
        if "确认" in text:
            reminder_id = reminder_id or self._pending_draft_id(history)
            if not reminder_id:
                return ReminderOutcome("请提供需要确认的提醒 ID，或在刚创建草稿的同一会话中明确确认。")
            return ReminderOutcome(self._status_answer(self.gateway.confirm(reminder_id, request_id), "确认"))
        if "暂停" in text:
            return self._manage("pause", reminder_id, request_id)
        if "取消" in text:
            return self._manage("cancel", reminder_id, request_id)
        if any(word in text for word in ("查看", "详情")):
            return self._manage("get", reminder_id, request_id)
        if any(word in text for word in ("查询", "列出", "有哪些")):
            filters = {}
            category = self._category(text, required=False)
            if category:
                filters["category"] = category
            rows = self.gateway.list(filters, request_id)
            if not rows:
                return ReminderOutcome("没有查到符合条件的统一提醒。")
            return ReminderOutcome("\n".join(self._summary(row) for row in rows))
        return self._create(text, conversation_id, request_id, now)

    def _create(self, text, conversation_id, request_id, now):
        category = self._category(text, required=True)
        times = self._times(text, now)
        if len(times) < 2:
            return ReminderOutcome("请明确提供事项日期时间和 Bark 提醒日期时间；缺少日期或存在歧义时我不会自行猜测。")
        event_at, notify_at = times[0], times[1]
        if event_at <= now or notify_at > event_at:
            return ReminderOutcome("请提供有效的未来事项时间，并确保 Bark 提醒时间不晚于事项时间。")
        amount_match = re.search(r"金额\s*([0-9]+(?:\.[0-9]{1,2})?)\s*元?", text)
        amount = amount_match.group(1) if amount_match else None
        payee_match = re.search(r"收款方\s*([^，,；;]+)", text)
        payee = payee_match.group(1).strip() if payee_match else None
        if category == "repayment" and amount and not payee:
            return ReminderOutcome("请明确提供还款提醒的收款方。")
        title = payee if category == "repayment" and payee else self._title(text)
        command = ReminderCreateCommand(
            idempotency_key=f"xiaole:{request_id}:reminder", title=title, category=category,
            event_at=event_at.isoformat(), notify_at=notify_at.isoformat(), amount=amount,
            notification_title=title, notification_body=title,
            metadata={"channel":"xiaole-v2", "conversation_id":conversation_id, "request_id":request_id},
        )
        row = self.gateway.create(command, request_id)
        if row.status == "draft":
            return ReminderOutcome(
                f"还款提醒草稿已创建。收款方：{payee}；金额：{amount} CNY；还款日期：{self._display(event_at)}；"
                f"Bark 提醒时间：{self._display(notify_at)}；提醒 ID：{row.reminder_id}；状态：draft。请明确确认是否启用。"
            )
        return ReminderOutcome(f"统一提醒已创建。提醒 ID：{row.reminder_id}；状态：{row.status}；事项时间：{self._display(event_at)}；Bark 提醒时间：{self._display(notify_at)}。")

    def _manage(self, operation, reminder_id, request_id):
        if not reminder_id:
            return ReminderOutcome("请提供需要操作的精确提醒 ID。")
        row = getattr(self.gateway, operation)(reminder_id, request_id)
        return ReminderOutcome(self._status_answer(row, {"get":"查看", "pause":"暂停", "cancel":"取消"}[operation]))

    @staticmethod
    def _absolute_times(text):
        matches = re.findall(r"(20\d{2})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})", text)
        result = []
        for year, month, day, hour, minute in matches:
            try: result.append(datetime(int(year), int(month), int(day), int(hour), int(minute), tzinfo=SHANGHAI))
            except ValueError: return []
        return result

    @classmethod
    def _times(cls, text, now):
        absolute = cls._absolute_times(text)
        if absolute:
            return absolute
        result = []
        for relative, hour, minute in re.findall(r"(今天|明天|后天)\s*(\d{1,2}):(\d{2})", text):
            days = {"今天": 0, "明天": 1, "后天": 2}[relative]
            try:
                date = (now + timedelta(days=days)).date()
                result.append(datetime(date.year, date.month, date.day, int(hour), int(minute), tzinfo=SHANGHAI))
            except ValueError:
                return []
        return result

    @staticmethod
    def _category(text, required=True):
        for word, value in (("还款","repayment"),("工作","work"),("日常","daily")):
            if word in text: return value
        return "daily" if required else None

    @staticmethod
    def _title(text):
        match = re.search(r"提醒[：:]\s*([^，,；;]+)", text)
        return (match.group(1).strip() if match else "小乐提醒")[:200]

    @staticmethod
    def _explicit_id(text):
        match = re.search(r"(?:提醒\s*)?(?:ID[：:]?\s*)?([A-Za-z0-9][A-Za-z0-9_-]{3,})", text, re.IGNORECASE)
        candidates = match.group(1) if match else None
        return candidates if candidates and any(char.isdigit() for char in candidates) else None

    @staticmethod
    def _pending_draft_id(history):
        ids = []
        for item in history:
            if item.get("role") == "assistant" and "状态：draft" in item.get("content", ""):
                match = re.search(r"提醒 ID：([A-Za-z0-9_-]+)", item["content"])
                if match: ids.append(match.group(1))
        return ids[-1] if len(set(ids)) == 1 else None

    @staticmethod
    def _display(value): return value.astimezone(SHANGHAI).strftime("%Y-%m-%d %H:%M")
    @staticmethod
    def _summary(row): return f"提醒 ID：{row.reminder_id}；标题：{row.title}；类别：{row.category}；状态：{row.status}"
    @classmethod
    def _status_answer(cls, row, operation): return f"提醒{operation}结果：提醒 ID：{row.reminder_id}；状态：{row.status}。"
