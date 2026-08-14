import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from xiaole_core.reminders import ReminderOrchestrator
from xiaole_core.schemas import ReminderResult


def result(status="enabled", category="work", amount=None, reminder_id="rem-1"):
    return ReminderResult(reminder_id=reminder_id, title="部署验收", category=category,
        event_at="2026-08-20T09:00:00+00:00", notify_at="2026-08-20T08:00:00+00:00",
        timezone="Asia/Shanghai", status=status, requires_confirmation=status == "draft", amount=amount)


class Gateway:
    def __init__(self, rows=None): self.calls=[]; self.rows=rows or []
    def create(self, command, request_id): self.calls.append(("create",command,request_id)); return self.rows.pop(0)
    def list(self, filters, request_id): self.calls.append(("list",filters,request_id)); return list(self.rows)
    def get(self, rid, request_id): self.calls.append(("get",rid,request_id)); return self.rows[0]
    def confirm(self, rid, request_id): self.calls.append(("confirm",rid,request_id)); return self.rows[0]
    def pause(self, rid, request_id): self.calls.append(("pause",rid,request_id)); return self.rows[0]
    def cancel(self, rid, request_id): self.calls.append(("cancel",rid,request_id)); return self.rows[0]


class ReminderOrchestratorTests(unittest.TestCase):
    now=datetime(2026,8,14,10,0,tzinfo=ZoneInfo("Asia/Shanghai"))

    def test_work_create_resolves_shanghai_times_without_delivery_claim(self):
        gateway=Gateway([result()]); orchestrator=ReminderOrchestrator(gateway)
        outcome=orchestrator.handle("创建工作提醒：部署验收，事项时间2026年8月20日17:00，Bark提醒时间2026年8月20日16:00",[],"c","r",self.now)
        command=gateway.calls[0][1]
        self.assertEqual((command.category,command.event_at,command.notify_at),("work","2026-08-20T17:00:00+08:00","2026-08-20T16:00:00+08:00"))
        self.assertNotIn("已推送",outcome.answer); self.assertNotIn("已送达",outcome.answer)

    def test_relative_dates_with_explicit_times_are_resolved_from_shanghai_today(self):
        gateway=Gateway([result()])
        ReminderOrchestrator(gateway).handle("创建工作提醒：开会，事项时间明天17:00，Bark提醒时间今天16:00",[],"c","r",self.now)
        command=gateway.calls[0][1]
        self.assertEqual(command.event_at,"2026-08-15T17:00:00+08:00")
        self.assertEqual(command.notify_at,"2026-08-14T16:00:00+08:00")

    def test_natural_question_lists_existing_repayment_reminders(self):
        gateway=Gateway([result(category="repayment")])
        outcome=ReminderOrchestrator(gateway).handle("最近是不是有几个还款提醒？",[],"c","r",self.now)
        self.assertEqual(gateway.calls[0][0], "list")
        self.assertEqual(gateway.calls[0][1], {"category": "repayment"})
        for value in (
            "标题：部署验收", "类别：repayment", "事项时间：2026-08-20 17:00",
            "提醒时间：2026-08-20 16:00", "状态：enabled", "提醒 ID：rem-1",
        ):
            self.assertIn(value, outcome.answer)

    def test_get_shows_complete_reminder_details(self):
        gateway=Gateway([result()])
        outcome=ReminderOrchestrator(gateway).handle("查看提醒 rem-1",[],"c","r",self.now)
        for value in (
            "标题：部署验收", "类别：work", "事项时间：2026-08-20 17:00",
            "提醒时间：2026-08-20 16:00", "状态：enabled", "提醒 ID：rem-1",
        ):
            self.assertIn(value, outcome.answer)

    def test_short_relative_reminder_uses_same_event_and_bark_time(self):
        gateway=Gateway([result(category="daily")])
        outcome=ReminderOrchestrator(gateway).handle("5分钟后用 Bark 提醒我洗完澡",[],"c","r",self.now)
        command=gateway.calls[0][1]
        self.assertEqual(command.title, "洗完澡")
        self.assertEqual(command.event_at, "2026-08-14T10:05:00+08:00")
        self.assertEqual(command.notify_at, "2026-08-14T10:05:00+08:00")
        self.assertIn("统一提醒已创建", outcome.answer)

    def test_missing_or_ambiguous_date_never_calls_gateway(self):
        for text in ("创建日常提醒：喝水，下午3点提醒", "创建工作提醒：开会，明天"):
            gateway=Gateway(); outcome=ReminderOrchestrator(gateway).handle(text,[],"c","r",self.now)
            self.assertEqual(gateway.calls,[]); self.assertIn("请",outcome.answer)

    def test_repayment_with_amount_is_draft_and_repeats_required_fields(self):
        gateway=Gateway([result("draft","repayment","128.50","draft-1")])
        outcome=ReminderOrchestrator(gateway).handle("创建还款提醒：收款方招商银行，金额128.50元，还款时间2026年8月20日17:00，Bark提醒时间2026年8月20日16:00",[],"c","r",self.now)
        self.assertEqual(gateway.calls[0][1].amount,"128.50")
        for value in ("招商银行","128.50","2026-08-20 17:00","2026-08-20 16:00","draft-1","draft"):
            self.assertIn(value,outcome.answer)

    def test_explicit_confirmation_recovers_exact_draft_from_same_history(self):
        gateway=Gateway([result("enabled","repayment","128.50","draft-1")])
        history=[{"role":"assistant","content":"还款提醒草稿已创建，提醒 ID：draft-1，状态：draft。请明确确认是否启用。"}]
        outcome=ReminderOrchestrator(gateway).handle("确认启用该提醒",history,"c","r",self.now)
        self.assertEqual(gateway.calls[0][:2],("confirm","draft-1")); self.assertIn("enabled",outcome.answer)

    def test_bare_confirmation_without_unique_draft_never_calls_gateway(self):
        gateway=Gateway(); outcome=ReminderOrchestrator(gateway).handle("确认",[],"c","r",self.now)
        self.assertEqual(gateway.calls,[]); self.assertIn("提醒 ID",outcome.answer)

    def test_list_get_pause_cancel_use_filters_and_exact_id(self):
        cases=(("查询工作提醒","list",{"category":"work"}), ("查看提醒 rem-1","get","rem-1"),
               ("暂停提醒 rem-1","pause","rem-1"),("取消提醒 rem-1","cancel","rem-1"))
        for text,operation,arg in cases:
            gateway=Gateway([result(status="paused" if operation=="pause" else "cancelled" if operation=="cancel" else "enabled")])
            ReminderOrchestrator(gateway).handle(text,[],"c","r",self.now)
            self.assertEqual(gateway.calls[0][0],operation); self.assertEqual(gateway.calls[0][1],arg)


if __name__ == "__main__": unittest.main()
