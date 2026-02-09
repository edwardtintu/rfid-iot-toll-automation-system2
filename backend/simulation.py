"""
Simulation module for HTMS - Hybrid Toll Management System
Generates realistic toll events and tests system behavior under various conditions
"""

import random
import time
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from threading import Thread
import requests
from typing import Dict, List, Optional


class HTMSSimulationEngine:
    """Main simulation engine for HTMS"""
    
    def __init__(self, api_base_url: str = "http://127.0.0.1:8000"):
        self.api_base = api_base_url
        self.running = False
        self.simulation_thread = None
        
        # Predefined test data
        self.test_cards = [
            {"uid": "5B88F75", "type": "CAR", "balance": 500.0},
            {"uid": "9C981B6", "type": "TRUCK", "balance": 2000.0},
            {"uid": "BE9E1E33", "type": "BUS", "balance": 1500.0},
            {"uid": "A1B2C3D", "type": "CAR", "balance": 100.0},
            {"uid": "E4F5G6H", "type": "TRUCK", "balance": 3000.0}
        ]
        
        self.readers = [
            {"id": "TOLL_READER_01", "secret": "reader_secret_01"},
            {"id": "TOLL_READER_02", "secret": "reader_secret_02"},
            {"id": "TOLL_READER_03", "secret": "reader_secret_03"}
        ]
        
        # Register readers initially
        self._register_readers()
    
    def _register_readers(self):
        """Register all readers with the backend"""
        for reader in self.readers:
            try:
                response = requests.post(
                    f"{self.api_base}/api/register_reader",
                    json={"reader_id": reader["id"], "secret": reader["secret"]}
                )
                if response.status_code == 200:
                    print(f"Registered reader: {reader['id']}")
                else:
                    print(f"Failed to register reader: {reader['id']}, {response.text}")
            except Exception as e:
                print(f"Error registering reader {reader['id']}: {str(e)}")
    
    def _generate_signature(self, uid: str, reader_id: str, timestamp: str, nonce: str, secret: str) -> str:
        """Generate HMAC-SHA256 signature for the request"""
        message = f"{uid}{reader_id}{timestamp}{nonce}".encode()
        signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
        return signature
    
    def _generate_event(self, reader_idx: int = 0, card_idx: int = 0, speed: Optional[int] = None) -> Dict:
        """Generate a single toll event"""
        reader = self.readers[reader_idx % len(self.readers)]
        card = self.test_cards[card_idx % len(self.test_cards)]
        
        if speed is None:
            speed = random.randint(30, 120)  # Random speed between 30-120 km/h
        
        timestamp = str(int(time.time()))
        nonce = f"nonce_{int(time.time() * 1000)}"
        signature = self._generate_signature(
            card["uid"], reader["id"], timestamp, nonce, reader["secret"]
        )
        
        return {
            "tag_hash": card["uid"].lower(),
            "reader_id": reader["id"],
            "speed": speed,
            "timestamp": timestamp,
            "nonce": nonce,
            "signature": signature,
            "key_version": "1"
        }
    
    def _send_event(self, event: Dict) -> Dict:
        """Send a single event to the backend"""
        try:
            response = requests.post(
                f"{self.api_base}/api/toll",
                json=event,
                headers={"Content-Type": "application/json"}
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def simulate_normal_traffic(self, duration_minutes: int = 5, events_per_minute: int = 10):
        """Simulate normal traffic flow"""
        print(f"Starting normal traffic simulation for {duration_minutes} minutes...")
        
        start_time = time.time()
        while time.time() - start_time < (duration_minutes * 60) and self.running:
            # Generate events at specified rate
            for _ in range(events_per_minute):
                if not self.running:
                    break
                    
                # Randomly select a reader and card
                reader_idx = random.randint(0, len(self.readers) - 1)
                card_idx = random.randint(0, len(self.test_cards) - 1)
                
                event = self._generate_event(reader_idx, card_idx)
                result = self._send_event(event)
                
                print(f"Event result: {result.get('action', 'unknown')} - {result.get('reasons', 'no reason')}")
                
                # Small delay between events
                time.sleep(0.1)
    
    def simulate_suspicious_behavior(self, duration_minutes: int = 2):
        """Simulate suspicious reader behavior to test trust mechanisms"""
        print(f"Starting suspicious behavior simulation for {duration_minutes} minutes...")
        
        start_time = time.time()
        while time.time() - start_time < (duration_minutes * 60) and self.running:
            # Select a specific reader to behave suspiciously
            reader = self.readers[0]  # Always use first reader for suspicious behavior
            
            # Generate multiple rapid events to trigger rate limiting
            for i in range(8):  # More than the rate limit
                if not self.running:
                    break
                    
                # Use the same card repeatedly to simulate potential fraud
                card = self.test_cards[0]
                
                # Generate event with potentially invalid data
                timestamp = str(int(time.time()))
                nonce = f"suspicious_nonce_{int(time.time() * 1000)}_{i}"
                
                # Use a potentially invalid signature to test authentication
                signature = self._generate_signature(
                    card["uid"], reader["id"], timestamp, nonce, "wrong_secret"
                )
                
                event = {
                    "tag_hash": card["uid"].lower(),
                    "reader_id": reader["id"],
                    "speed": random.randint(0, 300),  # Potentially invalid speed
                    "timestamp": timestamp,
                    "nonce": nonce,
                    "signature": signature,
                    "key_version": "1"
                }
                
                result = self._send_event(event)
                print(f"Suspicious event result: {result.get('action', 'unknown')}")
                
                # Very short delay to trigger rate limiting
                time.sleep(0.05)
            
            # Longer pause before next batch
            time.sleep(2)
    
    def simulate_replay_attack(self):
        """Simulate a replay attack by sending the same event twice"""
        print("Simulating replay attack...")
        
        # Generate a legitimate event first
        event = self._generate_event(0, 0)
        
        # Send it once (should be accepted)
        result1 = self._send_event(event)
        print(f"First event result: {result1.get('action', 'unknown')}")
        
        # Send the same event again (should be rejected as replay)
        result2 = self._send_event(event)
        print(f"Replay event result: {result2.get('action', 'unknown')}")
    
    def simulate_low_balance_scenarios(self):
        """Simulate scenarios with low balance cards"""
        print("Simulating low balance scenarios...")
        
        # Use a card with low balance
        low_balance_card = {"uid": "LOW_BALANCE_TEST", "type": "CAR", "balance": 50.0}
        
        reader = self.readers[0]
        timestamp = str(int(time.time()))
        nonce = f"low_bal_nonce_{int(time.time() * 1000)}"
        signature = self._generate_signature(
            low_balance_card["uid"], reader["id"], timestamp, nonce, reader["secret"]
        )
        
        event = {
            "tag_hash": low_balance_card["uid"].lower(),
            "reader_id": reader["id"],
            "speed": 60,
            "timestamp": timestamp,
            "nonce": nonce,
            "signature": signature,
            "key_version": "1"
        }
        
        result = self._send_event(event)
        print(f"Low balance event result: {result.get('action', 'unknown')}")
    
    def start_continuous_simulation(self, scenario: str = "mixed", interval_seconds: float = 1.0):
        """Start continuous simulation of a specific scenario"""
        self.running = True
        
        def simulation_loop():
            while self.running:
                if scenario == "normal":
                    self.simulate_normal_traffic(duration_minutes=1, events_per_minute=5)
                elif scenario == "suspicious":
                    self.simulate_suspicious_behavior(duration_minutes=1)
                elif scenario == "mixed":
                    # Alternate between different scenarios
                    self.simulate_normal_traffic(duration_minutes=1, events_per_minute=3)
                    time.sleep(5)
                    self.simulate_suspicious_behavior(duration_minutes=1)
                    time.sleep(5)
                else:
                    print(f"Unknown scenario: {scenario}")
                    break
                
                time.sleep(interval_seconds)
        
        self.simulation_thread = Thread(target=simulation_loop, daemon=True)
        self.simulation_thread.start()
        print(f"Started continuous simulation: {scenario}")
    
    def stop_simulation(self):
        """Stop the simulation"""
        self.running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=2)
        print("Simulation stopped")


def main():
    """Main function to run the simulation"""
    print("HTMS Simulation Engine")
    print("=" * 50)
    
    # Initialize simulation engine
    sim = HTMSSimulationEngine()
    
    # Run different simulation scenarios
    print("\n1. Testing replay attack protection...")
    sim.simulate_replay_attack()
    
    print("\n2. Testing low balance scenarios...")
    sim.simulate_low_balance_scenarios()
    
    print("\n3. Starting mixed simulation for 30 seconds...")
    sim.start_continuous_simulation(scenario="mixed", interval_seconds=2.0)
    
    # Let it run for 30 seconds
    time.sleep(30)
    
    # Stop simulation
    sim.stop_simulation()
    
    print("\nSimulation completed!")


if __name__ == "__main__":
    main()