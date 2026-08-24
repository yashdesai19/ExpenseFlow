from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.routers.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan events manager for FastAPI.
    Runs on startup and shutdown.
    """
    print(f"[START] Starting {settings.PROJECT_NAME} in [{settings.ENVIRONMENT}] mode")
    yield
    print(f"[STOP] Shutting down {settings.PROJECT_NAME}")


# Initialize FastAPI application instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Production-grade Expense Management API built with FastAPI, "
        "PostgreSQL, SQLAlchemy 2.0, Pydantic v2, and JWT Authentication."
    ),
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,      # Swagger UI
    redoc_url="/redoc" if settings.DEBUG else None,    # ReDoc UI
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ------------------------------------------------------------------------------
# 1. CORS (Cross-Origin Resource Sharing) Middleware
# ------------------------------------------------------------------------------
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ------------------------------------------------------------------------------
# 2. Security Headers Middleware (Production Hardening)
# ------------------------------------------------------------------------------
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Appends enterprise-grade HTTP security response headers to prevent
    Clickjacking, MIME sniffing, and cross-site scripting vulnerabilities.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ------------------------------------------------------------------------------
# 3. Centralized Exception Handlers (Safe Error Responses)
# ------------------------------------------------------------------------------
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Formats standard HTTP errors with a consistent JSON envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formats Pydantic request validation errors cleanly for frontend display."""
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err["loc"] if loc != "body")
        errors.append(f"{field}: {err['msg']}")
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": errors},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catches unexpected server crashes and prevents internal database traces
    or sensitive system paths from leaking to users.
    """
    # In production, log exc to monitoring tools (e.g. Sentry)
    print(f"[ERROR] Unhandled internal server error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


# ------------------------------------------------------------------------------
# 4. Root and Fallback Endpoints
# ------------------------------------------------------------------------------
@app.get("/", status_code=status.HTTP_200_OK, tags=["Root"])
async def root() -> dict[str, str]:
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "docs_url": "/docs",
        "health_check": f"{settings.API_V1_STR}/health",
    }


@app.get("/api/health", status_code=status.HTTP_200_OK, tags=["Health & Status"])
async def legacy_health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
    }


# ------------------------------------------------------------------------------
# 5. Mount Master API Router (/api/v1)
# ------------------------------------------------------------------------------
app.include_router(api_router, prefix=settings.API_V1_STR)

# ------------------------------------------------------------------------------
# 6. Mount Frontend Static Files (/ui)
# ------------------------------------------------------------------------------
import os
from fastapi.staticfiles import StaticFiles

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.isdir(FRONTEND_DIR):
    app.mount("/ui", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

