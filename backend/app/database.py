
import time
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from .config import settings

# Create SQLAlchemy engine
DATABASE_URL = settings.database_url

# Add retry logic for database connection
engine = None
for i in range(5):
    try:
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
        )
        conn = engine.connect()
        print("✅ Connected to Supabase!")
        conn.close()
        break
    except OperationalError as e:
        print(f"⚠️ Database connection failed (attempt {i+1}/5): {e}")
        time.sleep(5)

if engine is None:
    raise Exception("Failed to connect to the database after multiple retries.")

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

