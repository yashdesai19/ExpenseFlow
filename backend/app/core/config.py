import json
from typing import List, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized Application Configuration.
    Reads values from environment variables and .env file with automatic type validation.
    """
    # --------------------------------------------------------------------------
    # Application Info
    # --------------------------------------------------------------------------
    PROJECT_NAME: str = "ExpenseFlow Pro"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # --------------------------------------------------------------------------
    # Database
    # --------------------------------------------------------------------------
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/expenseflow_db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """Convert postgres:// to postgresql:// if needed (SQLAlchemy 2.0 compatibility)."""
        if isinstance(v, str):
            url = v.strip()
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            if not url:
                raise ValueError("DATABASE_URL must not be empty")
            return url
        return v

    @model_validator(mode="after")
    def validate_production_database_url(self) -> "Settings":
        if self.ENVIRONMENT.lower() == "production":
            if "localhost" in self.DATABASE_URL or "127.0.0.1" in self.DATABASE_URL or "::1" in self.DATABASE_URL:
                raise ValueError(
                    "DATABASE_URL cannot point to localhost in a production environment! "
                    "Please ensure the DATABASE_URL environment variable is correctly set in Render."
                )
        return self

    # --------------------------------------------------------------------------
    # Security / JWT
    # --------------------------------------------------------------------------
    JWT_SECRET_KEY: str = "dev-secret-key-change-this-in-production-expenseflow-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 Hours

    # --------------------------------------------------------------------------
    # CORS (Cross-Origin Resource Sharing)
    # --------------------------------------------------------------------------
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",
        "http://127.0.0.1:3000",
        "https://*.onrender.com",
        "http://localhost",
        "https://localhost",
        "capacitor://localhost",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        origins = []
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    origins = json.loads(v)
                except Exception:
                    pass
            else:
                origins = [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            origins = v

        # Always ensure mobile app origins are allowed in any environment config
        for mobile_origin in ["http://localhost", "https://localhost", "capacitor://localhost"]:
            if mobile_origin not in origins:
                origins.append(mobile_origin)

        return origins

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Single shared instance across the entire application
settings = Settings()
