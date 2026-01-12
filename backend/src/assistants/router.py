"""API router for AI assistants endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.assistants.models.api_models import AIAssistantListResponse, AIAssistantResponse
from src.database.evals_models import AIAssistant
from src.database.evals_session import get_evals_session

router = APIRouter(prefix="/assistants/api/v1", tags=["assistants"])


@router.get("/assistants", response_model=AIAssistantListResponse)
async def list_assistants(
    evals_session: AsyncSession = Depends(get_evals_session),
) -> AIAssistantListResponse:
    """
    List all available AI assistants.

    Returns all AI assistants from the database that can be used for
    report generation and prompt evaluation.
    """
    result = await evals_session.execute(
        select(AIAssistant).order_by(AIAssistant.id)
    )
    assistants = result.scalars().all()

    return AIAssistantListResponse(
        assistants=[
            AIAssistantResponse(id=a.id, name=a.name)
            for a in assistants
        ]
    )
