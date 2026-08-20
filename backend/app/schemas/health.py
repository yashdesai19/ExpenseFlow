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
