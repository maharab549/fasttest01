from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Determine which DB URL to use
selected_url = settings.supabase_database_url if settings.use_supabase and settings.supabase_database_url else settings.database_url

# Connection args
conn_args = {}
if selected_url.startswith("sqlite"):
    conn_args = {"check_same_thread": False}
elif selected_url.startswith("postgresql"):
    conn_args = {"connect_timeout": 10}

engine_kwargs = {"pool_pre_ping": True, "connect_args": conn_args}

if selected_url.startswith("postgresql"):
    engine_kwargs.update({"pool_size": 5, "max_overflow": 10, "pool_timeout": 10})

# Create engine
engine = create_engine(selected_url, **engine_kwargs)

# Session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base for models
Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
