from sqlalchemy import create_engine
from typing import Any, Dict
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Create SQLAlchemy engine
# pool_pre_ping=True helps prevent "server closed the connection unexpectedly" errors
# by checking if the database connection is still alive before using it.
# Decide which database URL to use
fallback_url = settings.database_url or "sqlite:///./marketplace.db"
supabase_url_val = getattr(settings, "supabase_database_url", None)
supabase_url = supabase_url_val if isinstance(supabase_url_val, str) else None
use_supabase = bool(getattr(settings, "use_supabase", False) and isinstance(supabase_url, str) and len(supabase_url) > 0)
selected_url: str = supabase_url if use_supabase and supabase_url is not None else fallback_url

# Build connect_args per driver
conn_args = {}
if selected_url.startswith("sqlite"):
    conn_args = {"check_same_thread": False}
elif selected_url.startswith("postgresql"):
    # Shorten initial failure if host is unreachable (e.g., DNS issue)
    conn_args = {"connect_timeout": 10}

engine_kwargs: Dict[str, Any] = {"pool_pre_ping": True, "connect_args": conn_args}
if selected_url.startswith("postgresql"):
    engine_kwargs.update({"pool_size": 5, "max_overflow": 10})

engine = create_engine(
    selected_url,
    **engine_kwargs,
)

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class for declarative models
Base = declarative_base()

def get_db():
    """
    Dependency to get a database session for each request.
    Ensures the database session is always closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
