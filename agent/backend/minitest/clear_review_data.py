"""Clear all review data from the database (ReviewData table only)."""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from backend.database.session import SessionLocal
from backend.database.model import ReviewData

def clear_review_data():
    db = SessionLocal()
    try:
        count = db.query(ReviewData).delete()
        db.commit()
        print(f"Deleted {count} ReviewData record(s)")
        print(f"Tables kept: sessions, messages, review_generation_tasks, ...")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    confirm = input("Delete ALL review data? Type 'yes' to confirm: ")
    if confirm.lower() == 'yes':
        clear_review_data()
    else:
        print("Cancelled.")
