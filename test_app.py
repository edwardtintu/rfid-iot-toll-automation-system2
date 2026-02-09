#!/usr/bin/env python3
"""
Test script to verify the HTMS application is working correctly
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_imports():
    """Test that all modules can be imported without errors"""
    print("Testing module imports...")
    
    try:
        from backend.database import SessionLocal, Card, init_db
        print("+ Database module imported successfully")
    except Exception as e:
        print(f"- Database module import failed: {e}")
        return False
    
    try:
        from backend.detection_updated import run_detection
        print("+ Detection module imported successfully")
    except Exception as e:
        print(f"- Detection module import failed: {e}")
        return False
        
    try:
        from backend.blockchain import send_to_chain
        print("+ Blockchain module imported successfully")
    except Exception as e:
        print(f"- Blockchain module import failed: {e}")
        return False
        
    try:
        from backend.app import app
        print("+ App module imported successfully")
    except Exception as e:
        print(f"- App module import failed: {e}")
        return False
        
    return True

def test_database_connection():
    """Test database connectivity and seeded data"""
    print("\nTesting database connection...")
    
    try:
        from backend.database import SessionLocal, Card, TollTariff
        db = SessionLocal()
        
        # Test if we can query cards
        cards = db.query(Card).all()
        print(f"+ Found {len(cards)} cards in database")
        
        # Test if we can query tariffs
        tariffs = db.query(TollTariff).all()
        print(f"+ Found {len(tariffs)} tariffs in database")
        
        db.close()
        return True
    except Exception as e:
        print(f"- Database connection failed: {e}")
        return False

def main():
    print("Starting HTMS Application Verification Tests...\n")
    
    success = True
    
    # Test imports
    if not test_imports():
        success = False
    
    # Test database
    if not test_database_connection():
        success = False
    
    print("\n" + "="*50)
    if success:
        print("+ All tests passed! The HTMS application is ready.")
        print("\nTo start the server, run:")
        print("cd backend && python -c \"import sys; sys.path.insert(0, '..'); from app import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000)\"")
    else:
        print("- Some tests failed. Please check the error messages above.")
    print("="*50)
    
    return success

if __name__ == "__main__":
    main()