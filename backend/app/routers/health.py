from fastapi import APIRouter, status
from app.core.config import settings
from app.schemas.health import AppVersionResponse, HealthCheckResponse

router = APIRouter(prefix="/health", tags=["Health & Status"])


@router.get(
    "",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Returns the operational status, environment, and version of the ExpenseFlow backend.",
)
async def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(
        status="ok",
        service=settings.PROJECT_NAME,
        version="1.0.0",
        environment=settings.ENVIRONMENT,
    )


@router.get(
    "/app-version",
    response_model=AppVersionResponse,
    status_code=status.HTTP_200_OK,
    summary="App Version Check",
    description="Returns the latest installable app version so the mobile client can show an update popup.",
)
@router.get("/version", response_model=AppVersionResponse, include_in_schema=False)
async def get_app_version() -> AppVersionResponse:
    return AppVersionResponse(
        latest_version=settings.APP_LATEST_VERSION,
        version_code=settings.APP_LATEST_VERSION_CODE,
        release_name=settings.APP_RELEASE_NAME,
        release_notes=settings.APP_RELEASE_NOTES,
        apk_url=settings.APP_APK_URL,
        web_url=settings.APP_WEB_URL,
        force_update=settings.APP_FORCE_UPDATE,
    )
