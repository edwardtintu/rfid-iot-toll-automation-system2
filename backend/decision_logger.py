import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from sqlalchemy.orm import Session
from database import DecisionTelemetry, SessionLocal

def log_decision(event_id, reader_id, trust_score, reader_status,
                 decision, reason, ml_a, ml_b, anomaly):
    """
    Log decision telemetry for audit and analysis
    
    Args:
        event_id: Unique identifier for the toll event
        reader_id: ID of the RFID reader
        trust_score: Current trust score of the reader
        reader_status: Current trust status of the reader (TRUSTED/DEGRADED/SUSPENDED)
        decision: Final decision (allow/block)
        reason: Reason(s) for the decision
        ml_a: Model A probability score
        ml_b: Model B probability score
        anomaly: Anomaly detection flag (0/1)
    """
    db = SessionLocal()
    try:
        telemetry_record = DecisionTelemetry(
            event_id=event_id,
            reader_id=reader_id,
            trust_score=trust_score,
            reader_status=reader_status,
            decision=decision,
            reason=reason,
            ml_score_a=ml_a,
            ml_score_b=ml_b,
            anomaly_flag=anomaly
        )
        db.add(telemetry_record)
        db.commit()
    except Exception as e:
        print(f"Error logging decision telemetry: {e}")
        db.rollback()
    finally:
        db.close()