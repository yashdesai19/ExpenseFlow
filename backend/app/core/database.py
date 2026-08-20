from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# ------------------------------------------------------------------------------
# SQLAlchemy 2.0 Engine & Connection Pool
# ------------------------------------------------------------------------------
# pool_pre_ping=True: Tests connections for liveness before vending them,
# preventing "server closed the connection unexpectedly" errors after idle periods.
# pool_size=10: Max 10 persistent connections maintained in the pool.
# max_overflow=20: Max 20 temporary connections when pool is exhausted under load.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,  # Logs all generated SQL queries to stdout in development
)

# ------------------------------------------------------------------------------
# Session Factory
# ------------------------------------------------------------------------------
# autocommit=False: Ensures explicit transaction management (requires session.commit())
# autoflush=False: Prevents premature flushing of incomplete changes to the DB
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ------------------------------------------------------------------------------
# Base Class for all SQLAlchemy Models
# ------------------------------------------------------------------------------
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI Dependency that yields a database session for each incoming HTTP request
    and guarantees that the session is closed when the request is complete.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
