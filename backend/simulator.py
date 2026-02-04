import random
import uuid
from datetime import datetime
import hashlib
import hmac
import time

def generate_toll_event():
    """Generate a realistic toll event that mimics RFID reader input"""
    reader_ids = ["RDR-001", "RDR-002", "RDR-003", "RDR-004", "RDR-005"]
    tag_ids = [
        "TAG-5B88F75", "TAG-9C981B6", "TAG-BE9E1E33", 
        "TAG-A2E15F20", "TAG-DEF4567", "TAG-GHI7890"
    ]
    
    return {
        "tag_hash": hashlib.sha256(random.choice(tag_ids).encode()).hexdigest(),
        "reader_id": random.choice(reader_ids),
        "speed": random.randint(30, 120),  # km/h
        "timestamp": int(time.time()),
        "nonce": str(uuid.uuid4())[:8],
        "key_version": "1"
    }

def generate_signature(event_data, secret="demo_secret"):
    """Generate HMAC signature for the event"""
    import hmac
    import hashlib
    
    message = f"{event_data['tag_hash']}{event_data['reader_id']}{event_data['timestamp']}{event_data['nonce']}".encode()
    signature = hmac.new(
        secret.encode(),
        message,
        hashlib.sha256
    ).hexdigest()
    
    return signature