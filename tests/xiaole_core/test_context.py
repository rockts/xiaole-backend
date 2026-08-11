import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from xiaole_core.context import CoreContextRepository, metadata, conversations, messages
from xiaole_core.errors import ConversationAccessDenied


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        engine = create_engine(f"sqlite:///{Path(self.tmp.name) / 'test.db'}")
        metadata.create_all(engine)
        self.sessions = sessionmaker(bind=engine, expire_on_commit=False)
        self.repo = CoreContextRepository(self.sessions)

    def tearDown(self):
        self.tmp.cleanup()

    def test_conversation_is_owned_and_history_is_capped(self):
        cid = self.repo.resolve("alice", None, "hello")
        for index in range(7):
            self.repo.append_exchange("alice", cid, f"u{index}", f"a{index}")
        self.assertEqual(len(self.repo.history("alice", cid)), 12)
        with self.assertRaises(ConversationAccessDenied):
            self.repo.resolve("bob", cid, "steal")
        with self.assertRaises(ConversationAccessDenied):
            self.repo.history("bob", cid)

    def test_only_conversation_and_message_rows_are_written(self):
        cid1 = self.repo.resolve("alice", None, "one")
        cid2 = self.repo.resolve("alice", None, "two")
        self.repo.append_exchange("alice", cid1, "u", "a")
        self.assertEqual(self.repo.history("alice", cid2), [])
        with self.sessions() as session:
            self.assertEqual(session.execute(conversations.select()).all().__len__(), 2)
            self.assertEqual(session.execute(messages.select()).all().__len__(), 2)


if __name__ == "__main__": unittest.main()
