"""SQLAlchemy 2.x Database Configuration & Session Management.

Configured for Supabase PostgreSQL with Session Pooler on port 5432 using psycopg 3.
"""

from typing import Generator, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from app.core.config import settings
from app.core.logging import logger


class Base(DeclarativeBase):
    """Base declarative class for all ResQMesh AI ORM models."""
    pass


# Connection pool configuration optimized for Supabase Session Pooler
connect_args = {}
if settings.DATABASE_URL.startswith("postgresql"):
    connect_args["connect_timeout"] = 10
elif settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=5,
)

# Session factory for transactional scopes
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_database_connection() -> Tuple[bool, str]:
    """Execute a lightweight PostgreSQL query ('SELECT 1') to verify connectivity.
    
    Returns:
        Tuple[bool, str]: (is_healthy, status_message)
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            if result == 1:
                try:
                    conn.execute(text("ALTER TABLE missions ADD COLUMN IF NOT EXISTS pending_route_polyline TEXT;"))
                    conn.execute(text("ALTER TABLE missions ADD COLUMN IF NOT EXISTS pending_eta_minutes DOUBLE PRECISION;"))
                    conn.execute(text("ALTER TABLE missions ADD COLUMN IF NOT EXISTS pending_replan_reason TEXT;"))
                    conn.execute(text("ALTER TABLE missions ADD COLUMN IF NOT EXISTS pending_replan_status VARCHAR;"))
                    conn.commit()
                except Exception as mig_err:
                    logger.warning(f"Schema migration warning: {mig_err}")
                return True, "Database connection healthy (SELECT 1 succeeded)."
            return False, "Unexpected result from database query."
    except Exception as e:
        logger.error(f"Database connectivity check failed: {type(e).__name__}: {e}")
        return False, f"Database connectivity error ({type(e).__name__})."
