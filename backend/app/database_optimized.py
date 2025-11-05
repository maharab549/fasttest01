"""
Enhanced Database Configuration with Connection Pooling
Production-ready database setup with PostgreSQL support and optimization
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from .config import settings
import logging

logger = logging.getLogger(__name__)

# Decide which database URL to use
fallback_url = settings.database_url or "sqlite:///./marketplace.db"
supabase_url_val = getattr(settings, "supabase_database_url", None)
supabase_url = supabase_url_val if isinstance(supabase_url_val, str) else None
use_supabase = bool(getattr(settings, "use_supabase", False) and isinstance(supabase_url, str) and len(supabase_url) > 0)
selected_url: str = supabase_url if use_supabase and supabase_url is not None else fallback_url

# Build connect_args and pool settings per driver
conn_args = {}
pool_settings = {}

if selected_url.startswith("sqlite"):
    # SQLite specific settings
    conn_args = {"check_same_thread": False}
    pool_settings = {
        "poolclass": NullPool,  # SQLite doesn't benefit from pooling
    }
    logger.info("Using SQLite database (development mode)")
    
elif selected_url.startswith("postgresql"):
    # PostgreSQL production settings with connection pooling
    conn_args = {
        "connect_timeout": 10,
        "options": "-c timezone=utc",  # Set timezone
    }
    pool_settings = {
        "poolclass": QueuePool,
        "pool_size": 20,  # Number of connections to maintain
        "max_overflow": 30,  # Additional connections allowed beyond pool_size
        "pool_timeout": 30,  # Seconds to wait for connection from pool
        "pool_recycle": 3600,  # Recycle connections after 1 hour
        "pool_pre_ping": True,  # Test connections before using
        "echo_pool": False,  # Set to True for debugging
    }
    logger.info("Using PostgreSQL database with connection pooling (production mode)")

# Create SQLAlchemy engine with optimization settings
engine = create_engine(
    selected_url,
    connect_args=conn_args,
    **pool_settings,
    echo=False,  # Set to True for SQL query logging
    future=True,  # Use SQLAlchemy 2.0 style
)

# Add connection pool event listeners for monitoring (PostgreSQL only)
if selected_url.startswith("postgresql"):
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Log new connections"""
        logger.debug("New database connection established")
    
    @event.listens_for(engine, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy):
        """Log connection checkout from pool"""
        logger.debug("Connection checked out from pool")
    
    @event.listens_for(engine, "checkin")
    def receive_checkin(dbapi_conn, connection_record):
        """Log connection return to pool"""
        logger.debug("Connection returned to pool")

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Prevent expired object errors
)

# Create a Base class for declarative models
Base = declarative_base()

def get_db():
    """
    Dependency to get a database session for each request.
    Ensures the database session is always closed after the request.
    Includes error handling and logging.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def get_db_stats():
    """
    Get database connection pool statistics (PostgreSQL only)
    Returns pool size, connections in use, and available connections
    """
    if selected_url.startswith("postgresql"):
        pool = engine.pool
        try:
            pool_obj = getattr(pool, '_pool', None)
            pool_size = pool_obj.qsize() if pool_obj and hasattr(pool_obj, 'qsize') else 0
            return {
                "pool_size": pool_size,
                "overflow": getattr(pool, '_overflow', 0),
                "status": "healthy",
            }
        except Exception:
            return {"status": "unknown"}
    return None

def check_db_connection():
    """
    Check if database connection is healthy
    Returns True if connection is successful, False otherwise
    """
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return False
