"""API models for assistants endpoints."""

from pydantic import BaseModel, Field


class AIAssistantResponse(BaseModel):
    """Response model for a single AI assistant."""

    id: int = Field(..., description="Unique identifier for the assistant")
    name: str = Field(..., description="Name of the AI assistant (e.g., 'ChatGPT')")


class AIAssistantListResponse(BaseModel):
    """Response model for listing AI assistants."""

    assistants: list[AIAssistantResponse] = Field(
        ..., description="List of available AI assistants"
    )
