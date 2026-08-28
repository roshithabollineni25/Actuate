"""Script to reset PostgreSQL operational demo data and restart identity sequences for ACTUATE demo."""

import sys
import os
from sqlalchemy import text

sys.path.insert(0, os.path.abspath("."))

from app.db.session import SessionLocal

def reset_demo_database():
    db = SessionLocal()
    try:
        print("=== RESETTING ACTUATE DEMO DATABASE ===")

        # Truncate operational tables and restart identity sequences
        db.execute(text("TRUNCATE TABLE audit_logs, missions, incidents, road_statuses RESTART IDENTITY CASCADE;"))
        
        # Reset rescue team status back to AVAILABLE
        db.execute(text("UPDATE rescue_teams SET status = 'AVAILABLE';"))

        db.commit()
        print("[+] Wiped operational tables: audit_logs, missions, incidents, road_statuses")
        print("[+] Restarted identity sequences for Incidents, Missions, AuditLogs, RoadStatuses to 1")
        print("[+] Reset all Rescue Teams to AVAILABLE")
        print("=== ACTUATE DEMO DATABASE CLEANED SUCCESSFULLY ===")
    except Exception as e:
        db.rollback()
        print(f"FAILED to reset demo database: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    reset_demo_database()
