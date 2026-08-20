from fastapi import APIRouter, status
from app.core.config import settings
from app.schemas.health import HealthCheckResponse

router = APIRouter(prefix="/health", tags=["Health & Status"])


@router.get(
    "",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Returns the operational status, environment, and version of the ExpenseFlow backend.",
)
async def health_check() -> HealthCheckResponse:
    """
    Performs a liveness probe to verify that the FastAPI ASGI server is actively running.
    """
    return HealthCheckResponse(
        status="ok",
        service=settings.PROJECT_NAME,
        version="1.0.0",
        environment=settings.ENVIRONMENT,
    )
