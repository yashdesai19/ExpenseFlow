import pytest
from sqlalchemy import text
from app.core.database import engine, SessionLocal, get_db
from app.models import Base


def test_database_engine_connection():
    """Verify that SQLAlchemy engine can successfully connect to PostgreSQL."""
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_get_db_session_lifecycle():
    """Verify that get_db yields a live session and closes it on completion."""
    db_gen = get_db()
    db = next(db_gen)
    try:
        assert db.is_active is True
        result = db.execute(text("SELECT 1"))
        assert result.scalar() == 1
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass  # Expected cleanup behavior


def test_registered_models_in_metadata():
    """Ensure all core financial domain tables are declared in Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    expected_tables = {
        "users",
        "categories",
        "expenses",
        "budgets",
        "recurring_expenses",
        "audit_logs",
        "user_settings",
    }
    assert expected_tables.issubset(table_names)
