"""Router for prompts-related endpoints."""

from fastapi import APIRouter, Query
from src.utils.url_validator import validate_and_normalize_url

router = APIRouter(prefix="/prompts/api/v1", tags=["prompts"])


@router.get("/topics")
async def get_topics(url: str = Query(..., description="URL of the domain to analyze")):
    """
    Get topics/keywords relevant for a business and their industry.

    Args:
        url: The URL of the domain to analyze

    Returns:
        List of topic strings
    """
    # Validate and normalize the URL
    await validate_and_normalize_url(url)

    # Return hardcoded topics
    return ["GEO", "AI search", "Brand monitoring"]
