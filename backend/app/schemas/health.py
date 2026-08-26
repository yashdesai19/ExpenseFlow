from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    """
    Response schema for the service health check endpoint.
    Used for monitoring uptime, deployment validation, and load-balancer probes.
    """
    status: str = Field(default="ok", description="Current service health status")
    service: str = Field(default="ExpenseFlow API", description="Name of the running microservice/backend")
    version: str = Field(default="1.0.0", description="API semantic version")
    environment: str = Field(default="development", description="Current operating environment")


class AppVersionResponse(BaseModel):
    """Latest installable Android build, used by the in-app update popup."""
    latest_version: str = Field(description="Semantic version shown to the user, e.g. 1.1.0")
    version_code: int = Field(description="Integer versionCode; must be higher than the installed APK to trigger an update")
    release_name: str = Field(description="Short title for this release")
    release_notes: list[str] = Field(default_factory=list, description="Bullet points shown in the update popup")
    apk_url: str = Field(description="Direct download URL for the signed APK")
    web_url: str = Field(description="Fallback web app URL")
    force_update: bool = Field(default=False, description="If true, the user cannot dismiss the popup")
