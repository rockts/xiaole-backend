import os
import unittest
import asyncio
from unittest.mock import Mock, patch

from apscheduler.schedulers.background import BackgroundScheduler

os.environ["DATABASE_URL"] = "sqlite:///:memory:"


class LegacyReminderRetirementTests(unittest.TestCase):
    def test_legacy_reminder_routes_are_not_registered(self):
        with patch("sqlalchemy.sql.schema.MetaData.create_all"):
            from main import app

        route_paths = {route.path for route in app.routes}
        self.assertNotIn("/reminders", route_paths)
        self.assertNotIn("/api/reminders", route_paths)

    def test_background_scheduler_only_registers_non_reminder_jobs(self):
        with patch("sqlalchemy.sql.schema.MetaData.create_all"):
            from scheduler import ReminderScheduler

        scheduler = ReminderScheduler.__new__(ReminderScheduler)
        scheduler.scheduler = BackgroundScheduler()
        scheduler.proactive_chat = Mock()
        scheduler.memory_manager = Mock()
        scheduler.llm_gateway = Mock()
        scheduler.is_running = False

        with patch.object(scheduler.scheduler, "start"):
            scheduler.start()

        self.assertEqual(
            {job.id for job in scheduler.scheduler.get_jobs()},
            {
                "check_proactive_chat",
                "cleanup_old_memories",
                "conflict_detector_daily",
            },
        )

    def test_legacy_reminder_tool_is_not_public(self):
        with patch("sqlalchemy.sql.schema.MetaData.create_all"):
            import tools

        self.assertNotIn("reminder_tool", tools.__all__)
        self.assertFalse(hasattr(tools, "reminder_tool"))

    def test_proactive_chat_keeps_the_shared_websocket_channel(self):
        with patch("sqlalchemy.sql.schema.MetaData.create_all"):
            from scheduler import ReminderScheduler

        async def broadcast(_message):
            return None

        scheduler = ReminderScheduler.__new__(ReminderScheduler)
        scheduler.proactive_chat = Mock()
        scheduler.proactive_chat.should_initiate_chat.return_value = {
            "should_chat": True,
            "reason": "daily_check_in",
            "message": "今天过得怎么样？",
            "priority": 2,
            "metadata": {},
        }
        scheduler.llm_gateway = Mock()
        scheduler.llm_gateway.acquire_execution_lease.return_value = True
        loop = Mock()

        scheduler.configure_websocket(broadcast, loop)
        with patch.object(asyncio, "run_coroutine_threadsafe") as dispatch:
            scheduler.check_proactive_chat()

        dispatch.assert_called_once()
        self.assertIs(dispatch.call_args.args[1], loop)
        scheduler.proactive_chat.mark_chat_initiated.assert_called_once_with(
            "default_user", "daily_check_in", "今天过得怎么样？"
        )
        dispatch.call_args.args[0].close()

    def test_task_delete_cannot_cascade_into_legacy_reminders(self):
        with patch("sqlalchemy.sql.schema.MetaData.create_all"):
            from modules.task_manager import TaskManager

        cursor = Mock()
        cursor.fetchone.return_value = (True,)
        connection = Mock()
        connection.cursor.return_value = cursor
        manager = TaskManager.__new__(TaskManager)
        manager._get_connection = Mock(return_value=connection)

        self.assertFalse(manager.delete_task(42))
        statements = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertFalse(any(statement.startswith("DELETE FROM tasks") for statement in statements))
        connection.commit.assert_not_called()

    def test_backend_served_client_has_no_legacy_reminder_surface(self):
        with patch("sqlalchemy.sql.schema.MetaData.create_all"):
            from fastapi.testclient import TestClient
            from main import app

        client = TestClient(app)
        html = client.get("/static/index.html").text
        app_js = client.get("/static/js/app.js").text
        legacy_js = client.get("/static/js/legacy-inline.js").text
        theme_js = client.get("/static/js/modules/theme.js").text

        self.assertNotIn('data-tab="reminders"', html)
        self.assertNotIn('id="reminders"', html)
        self.assertNotIn('id="reminderNotifications"', html)
        self.assertNotIn("loadReminders", app_js)
        self.assertNotIn("initRemindersTasks", app_js)
        self.assertNotIn("message.type === 'reminder'", legacy_js)
        self.assertNotIn("/api/reminders", legacy_js)
        self.assertNotIn("reminderNotifications", legacy_js)
        self.assertNotIn("reminderNotifications", theme_js)


if __name__ == "__main__":
    unittest.main()
