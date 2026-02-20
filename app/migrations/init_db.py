"""Database initialization script - creates all tables"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, db
from models import Project, Alert, AlertAcknowledgment, AlertHistory


def init_db():
    """Initialize database and create all tables"""
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✓ Database initialized successfully!")
        print("  - projects table")
        print("  - alerts table")
        print("  - alert_acknowledgments table")
        print("  - alert_history table")


if __name__ == '__main__':
    init_db()
