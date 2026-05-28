"""Clear all data from SQLite database"""
import os
import sys
from pathlib import Path

# Add project root directory to path to import backend modules
project_root = Path(__file__).parent.parent / "agent"
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.orm import Session
from backend.database.session import SessionLocal
from backend.database.model import Session as ChatSession, Message, ReviewData, ReviewGenerationTask

def clear_database():
    """Clear all data from SQLite database"""
    db: Session = SessionLocal()

    try:
        print("=" * 60)
        print("Clearing SQLite Database")
        print("=" * 60)

        # Count before deletion
        session_count = db.query(ChatSession).count()
        message_count = db.query(Message).count()
        review_data_count = db.query(ReviewData).count()
        review_task_count = db.query(ReviewGenerationTask).count()

        print(f"Sessions to delete: {session_count}")
        print(f"Messages to delete: {message_count}")
        print(f"Review data to delete: {review_data_count}")
        print(f"Review tasks to delete: {review_task_count}")

        if session_count == 0 and message_count == 0 and review_data_count == 0 and review_task_count == 0:
            print("Database is already empty.")
            return

        # Delete in order of foreign key dependencies
        if review_task_count > 0:
            deleted_tasks = db.query(ReviewGenerationTask).delete()
            print(f"Deleted {deleted_tasks} review tasks")

        if review_data_count > 0:
            deleted_review_data = db.query(ReviewData).delete()
            print(f"Deleted {deleted_review_data} review data")

        # Delete messages
        if message_count > 0:
            deleted_messages = db.query(Message).delete()
            print(f"Deleted {deleted_messages} messages")

        # Delete sessions
        if session_count > 0:
            deleted_sessions = db.query(ChatSession).delete()
            print(f"Deleted {deleted_sessions} sessions")

        # Commit the transaction
        db.commit()

        # Verify deletion
        remaining_sessions = db.query(ChatSession).count()
        remaining_messages = db.query(Message).count()

        print()
        print("=" * 60)
        print("Database Cleared Successfully!")
        print(f"Remaining sessions: {remaining_sessions}")
        print(f"Remaining messages: {remaining_messages}")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"Error clearing database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    confirm = input("This will delete ALL data in SQLite database. Type 'yes' to confirm: ")
    if confirm.lower() == 'yes':
        clear_database()
    else:
        print("Cancelled.")