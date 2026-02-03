import os
import time
from sqlalchemy import create_engine, text

def wait_for_db():
    """Wait for database to be ready"""
    max_attempts = 30
    attempt = 0

    # Import here to ensure environment variables are loaded
    from database import DB_URL

    while attempt < max_attempts:
        try:
            # Create a temporary engine to test connection
            temp_engine = create_engine(DB_URL)
            with temp_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database connection successful!")
            return True
        except Exception as e:
            print(f"Attempt {attempt + 1}: Waiting for database... Error: {e}")
            time.sleep(2)
            attempt += 1

    print("Failed to connect to database after maximum attempts")
    return False

def init_tables():
    """Initialize database tables"""
    try:
        # Wait for database to be ready
        if not wait_for_db():
            raise Exception("Database not available")

        # Import after environment is set to ensure correct DB_URL
        from database import Base, engine

        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully!")
        return True
    except Exception as e:
        print(f"Error initializing tables: {e}")
        return False

if __name__ == "__main__":
    print("Starting database initialization...")
    success = init_tables()
    if success:
        print("Database initialization completed successfully!")
    else:
        print("Database initialization failed!")
        exit(1)