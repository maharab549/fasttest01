from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Add this line
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
        yield db
    finally:
        db.close()

