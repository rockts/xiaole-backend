from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, String, Table, Text, and_, select

from .errors import ConversationAccessDenied


metadata = MetaData()
conversations = Table(
    "conversations", metadata,
    Column("id", Integer, primary_key=True),
    Column("session_id", String(100), unique=True, index=True),
    Column("user_id", String(50), default="default_user"),
    Column("title", String(200)),
    Column("pinned", Boolean, default=False),
    Column("created_at", DateTime, default=datetime.now),
    Column("updated_at", DateTime, default=datetime.now),
)
messages = Table(
    "messages", metadata,
    Column("id", Integer, primary_key=True),
    Column("session_id", String(100), index=True),
    Column("role", String(20)),
    Column("content", Text),
    Column("created_at", DateTime, default=datetime.now),
    Column("image_path", String(500)),
)


class CoreContextRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def resolve(self, user_id: str, conversation_id: str | None, first_message: str) -> str:
        with self.session_factory() as session:
            if conversation_id:
                owned = session.execute(select(conversations.c.session_id).where(and_(conversations.c.session_id == conversation_id, conversations.c.user_id == user_id))).scalar_one_or_none()
                if not owned:
                    raise ConversationAccessDenied("conversation does not belong to current user")
                return conversation_id
            conversation_id = str(uuid.uuid4())
            session.execute(conversations.insert().values(session_id=conversation_id, user_id=user_id, title=self._title(first_message), pinned=False, created_at=datetime.now(), updated_at=datetime.now()))
            session.commit()
            return conversation_id

    def history(self, user_id: str, conversation_id: str, limit: int = 12) -> list[dict]:
        with self.session_factory() as session:
            owned = session.execute(select(conversations.c.session_id).where(and_(conversations.c.session_id == conversation_id, conversations.c.user_id == user_id))).scalar_one_or_none()
            if not owned:
                raise ConversationAccessDenied("conversation does not belong to current user")
            rows = session.execute(select(messages.c.role, messages.c.content).where(messages.c.session_id == conversation_id).order_by(messages.c.created_at.desc(), messages.c.id.desc()).limit(min(limit, 12))).all()
            return [{"role": row.role, "content": row.content} for row in reversed(rows)]

    def append_exchange(self, user_id: str, conversation_id: str, user_message: str, assistant_message: str) -> None:
        self.resolve(user_id, conversation_id, user_message)
        now = datetime.now()
        with self.session_factory() as session:
            session.execute(messages.insert(), [
                {"session_id": conversation_id, "role": "user", "content": user_message, "created_at": now},
                {"session_id": conversation_id, "role": "assistant", "content": assistant_message, "created_at": now},
            ])
            session.execute(conversations.update().where(and_(conversations.c.session_id == conversation_id, conversations.c.user_id == user_id)).values(updated_at=now))
            session.commit()

    @staticmethod
    def _title(message: str) -> str:
        cleaned = " ".join(message.split())
        return (cleaned[:20] + ("..." if len(cleaned) > 20 else "")) or "新对话"
