import os
import shutil

# Delete the database file
db_path = "backend/storage/toll_data.db"
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Deleted {db_path}")
else:
    print(f"{db_path} does not exist")

# Initialize fresh database
import sys
sys.path.append("backend")
from database import init_db

init_db()
print("Database initialized successfully!")
