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


def test_production_database_url_validation():
    """Verify that settings validation raises ValueError if database URL points to localhost in production."""
    from pydantic import ValidationError
    from app.core.config import Settings

    # Case 1: production and localhost should raise ValidationError
    with pytest.raises(ValidationError) as excinfo:
        Settings(ENVIRONMENT="production", DATABASE_URL="postgresql://postgres:postgres@localhost:5432/db")
    assert "DATABASE_URL cannot point to localhost in a production environment" in str(excinfo.value)

    # Case 2: production and 127.0.0.1 should raise ValidationError
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production", DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/db")

    # Case 3: production and ::1 should raise ValidationError
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production", DATABASE_URL="postgresql://postgres:postgres@[::1]:5432/db")

    # Case 4: production and non-localhost (Render DB URL) should be valid
    prod_url = "postgresql://user:pass@dpg-xxx-a.oregon-postgres.render.com/db"
    settings = Settings(ENVIRONMENT="production", DATABASE_URL=prod_url)
    assert settings.DATABASE_URL == prod_url
