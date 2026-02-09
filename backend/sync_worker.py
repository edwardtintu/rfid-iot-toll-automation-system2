import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from database import SessionLocal
from datetime import datetime

def sync_pending_events(write_to_blockchain):
    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                SELECT event_id
                FROM blockchain_queue
                WHERE status = "PENDING"
            """)
        )

        for row in result:
            event_id = row.event_id
            try:
                write_to_blockchain(event_id)
                db.execute(
                    text("""
                        UPDATE blockchain_queue
                        SET status = "SYNCED",
                            last_attempt = :ts
                        WHERE event_id = :event_id
                    """),
                    {"event_id": event_id, "ts": datetime.utcnow()}
                )
            except Exception:
                pass

        db.commit()
    finally:
        db.close()