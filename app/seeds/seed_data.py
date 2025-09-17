"""
Seed data creation for Clarity Local Runner development environment.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from database.session import SessionLocal
from sqlalchemy.orm import Session


def create_seed_data():
    """Create basic seed data for development."""
    db = SessionLocal()
    try:
        # Clear existing data first
        clear_all_data(db)

        # Create basic workflow orchestration seed data
        # This will be expanded as the workflow system is implemented
        
        print("✅ Basic seed data structure created successfully!")
        print("📝 Note: Workflow-specific seed data will be added as the system develops")

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"❌ Error creating seed data: {e}")
        raise
    finally:
        db.close()


def clear_all_data(db: Optional[Session] = None):
    """Clear all data from the database."""
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False

    try:
        # Clear workflow orchestration data when models are implemented
        # This will be expanded as the data models are created
        
        if should_close:
            db.commit()
            print("✅ All data cleared successfully!")

    except Exception as e:
        if should_close:
            db.rollback()
        print(f"❌ Error clearing data: {e}")
        raise
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    create_seed_data()
