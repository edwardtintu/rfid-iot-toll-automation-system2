import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from database import SessionLocal
from datetime import datetime

def enqueue_blockchain_event(event_id):
    db = SessionLocal()
    try:
        db.execute(
            text("""
                INSERT INTO blockchain_queue (event_id, status)
                VALUES (:event_id, 'PENDING')
            """),
            {"event_id": event_id}
        )
        db.commit()
    finally:
        db.close()

def mark_event_synced(event_id):
    db = SessionLocal()
    try:
        db.execute(
            text("""
                UPDATE blockchain_queue
                SET status = 'SYNCED',
                    last_attempt = :ts
                WHERE event_id = :event_id
            """),
            {"event_id": event_id, "ts": datetime.utcnow()}
        )
        db.commit()
    finally:
        db.close()