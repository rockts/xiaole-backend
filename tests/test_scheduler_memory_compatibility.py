import unittest
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

original_database_url = os.environ.get("DATABASE_URL")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
with patch("sqlalchemy.sql.schema.MetaData.create_all"):
    import modules.proactive_chat as proactive_chat_module
    from db_setup import Memory, Message, ProactiveQuestion, UserBehavior
    from modules.proactive_chat import ProactiveChat
    from scheduler import ReminderScheduler
if original_database_url is None:
    os.environ.pop("DATABASE_URL", None)
else:
    os.environ["DATABASE_URL"] = original_database_url


class ReminderManagerStub:
    websocket_callback = None


class SchedulerMemoryCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        for table in (
            Memory.__table__,
            Message.__table__,
            ProactiveQuestion.__table__,
            UserBehavior.__table__,
        ):
            table.create(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.original_session_factory = proactive_chat_module.SessionLocal
        proactive_chat_module.SessionLocal = self.session_factory

        session = self.session_factory()
        try:
            session.add(
                Memory(
                    content="一条旧记忆",
                    tag="facts",
                    created_at=datetime.now() - timedelta(days=1),
                )
            )
            session.commit()
        finally:
            session.close()

    def tearDown(self):
        proactive_chat_module.SessionLocal = self.original_session_factory
        self.engine.dispose()

    def test_hourly_scheduler_job_accepts_legacy_memory_schema(self):
        scheduler = ReminderScheduler.__new__(ReminderScheduler)
        scheduler.proactive_chat = ProactiveChat()
        scheduler.reminder_manager = ReminderManagerStub()
        error_log = Mock()

        original_error = __import__("scheduler").logger.error
        __import__("scheduler").logger.error = error_log
        try:
            scheduler.check_proactive_chat()
        finally:
            __import__("scheduler").logger.error = original_error

        error_log.assert_not_called()

    def test_interesting_topics_reads_created_at_from_existing_memory(self):
        session = self.session_factory()
        try:
            result = ProactiveChat()._check_interesting_topics(
                session, "default_user"
            )
        finally:
            session.close()

        self.assertTrue(result["should_chat"])
        self.assertEqual(result["metadata"]["memory_content"], "一条旧记忆")


if __name__ == "__main__":
    unittest.main()
