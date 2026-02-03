from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration using environment variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "htms")
DB_USER = os.getenv("DB_USER", "htms_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "htms_pass")

# Use environment variable for DB path, fallback to default
# If PostgreSQL environment variables are set, use PostgreSQL; otherwise use SQLite
if os.getenv("USE_POSTGRES", "false").lower() == "true":
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///backend/storage/toll_data.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)