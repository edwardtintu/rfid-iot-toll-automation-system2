import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal, TollEvent, Reader, ReaderViolation, ReaderTrust
from sqlalchemy import func, and_

def detect_outlier_reader(reader_id, window_minutes=10):
    """
    Detect if a reader is behaving abnormally compared to peer readers
    by comparing transaction counts in a time window.
    
    Args:
        reader_id: ID of the reader to check
        window_minutes: Time window to analyze (default 10 minutes)
    
    Returns:
        bool: True if reader is an outlier, False otherwise
    """
    db = SessionLocal()
    try:
        # Calculate the time threshold
        time_threshold = datetime.utcnow() - timedelta(minutes=window_minutes)
        
        # Get all readers in the same plaza/region (for now, just all active readers)
        all_readers = db.query(Reader.reader_id).filter(Reader.status == "ACTIVE").all()
        all_reader_ids = [r.reader_id for r in all_readers]
        
        # Calculate average transaction count per reader in the time window
        avg_query = db.query(func.avg(reader_counts.c.cnt)).select_from(
            db.query(
                TollEvent.reader_id,
                func.count(TollEvent.event_id).label('cnt')
            )
            .filter(TollEvent.timestamp > time_threshold.timestamp())
            .filter(TollEvent.reader_id.in_(all_reader_ids))
            .group_by(TollEvent.reader_id)
            .subquery('reader_counts')
        )
        
        avg_cnt_result = avg_query.first()
        avg_cnt = avg_cnt_result[0] if avg_cnt_result and avg_cnt_result[0] else 0
        
        # Get transaction count for the specific reader
        reader_cnt = db.query(func.count(TollEvent.event_id)).filter(
            and_(
                TollEvent.reader_id == reader_id,
                TollEvent.timestamp > time_threshold.timestamp()
            )
        ).scalar()
        
        # Simple outlier rule: if reader's count is significantly higher than average
        # Using 3x multiplier as threshold (configurable)
        multiplier_threshold = 3
        if avg_cnt > 0 and reader_cnt > (avg_cnt * multiplier_threshold):
            return True  # This reader is an outlier
        return False
    except Exception as e:
        print(f"Error in cross-reader analysis: {e}")
        return False
    finally:
        db.close()
