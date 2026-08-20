from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    """Generic message response schema"""
    message: str = Field(..., description="Human-readable response or status message")
