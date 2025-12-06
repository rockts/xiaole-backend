from datetime import datetime, timedelta
from sqlalchemy import or_
from backend.db_setup import SessionLocal, Memory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_recall(tag):
    session = SessionLocal()
    try:
        print(f"\nTesting recall for tag: '{tag}'")

        # Simulate recall_recent logic
        hours = 24 * 365 * 10
        time_threshold = datetime.now() - timedelta(hours=hours)

        query = session.query(Memory).filter(
            Memory.created_at >= time_threshold
        )

        if tag:
            # Support prefix matching for tags (case-insensitive)
            query = query.filter(
                or_(
                    Memory.tag.ilike(tag),
                    Memory.tag.ilike(f"{tag}:%")
                )
            )

        count = query.count()
        print(f"Found {count} memories.")

        results = query.limit(5).all()
        for m in results:
            print(f"  - [{m.tag}] {m.content[:50]}...")

    finally:
        session.close()


if __name__ == "__main__":
    test_recall("conversation")
    test_recall("facts")
    test_recall("document")
