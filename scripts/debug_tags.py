from sqlalchemy import func
from db_setup import SessionLocal, Memory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def list_tags():
    session = SessionLocal()
    try:
        # Get all distinct tags
        tags = session.query(Memory.tag).distinct().all()
        print("All distinct tags in DB:")
        for t in tags:
            print(f"  - {t[0]}")

        # Count by tag
        stats = session.query(Memory.tag, func.count(
            Memory.id)).group_by(Memory.tag).all()
        print("\nTag counts:")
        for tag, count in stats:
            print(f"  - {tag}: {count}")

    finally:
        session.close()


if __name__ == "__main__":
    list_tags()
