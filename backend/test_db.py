from db import engine

try:
    with engine.connect() as conn:
        print("SUCCESS: Connected to Supabase database")
except Exception as e:
    print("ERROR: Connection failed:", str(e))