import pytest
from sqlalchemy import inspect
from app.core.database import engine
from app.models import Base


def test_database_tables_exist_in_postgres():
    """Verify that Alembic migrations created all physical tables in PostgreSQL."""
    inspector = inspect(engine)
    physical_tables = set(inspector.get_table_names())
    
    # Must include Alembic metadata table
    assert "alembic_version" in physical_tables

    # Must include all 7 business domain tables
    expected_tables = {
        "users",
        "categories",
        "expenses",
        "budgets",
        "recurring_expenses",
        "audit_logs",
        "user_settings",
    }
    assert expected_tables.issubset(physical_tables)


def test_expenses_table_columns_and_indexes():
    """Verify that the expenses table contains the precise columns and indexes."""
    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("expenses")}
    
    assert "id" in columns
    assert "amount" in columns
    assert "user_id" in columns
    assert "category_id" in columns
    assert "date" in columns
    assert "account" in columns

    # Verify foreign keys
    foreign_keys = inspector.get_foreign_keys("expenses")
    fk_targets = {fk["referred_table"] for fk in foreign_keys}
    assert "users" in fk_targets
    assert "categories" in fk_targets
