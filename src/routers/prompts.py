"""Router for prompts-related endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.config.countries import get_location_name
from src.services.dataforseo_service import DataForSEOService, get_dataforseo_service
from src.utils.url_validator import validate_and_normalize_url

router = APIRouter(prefix="/prompts/api/v1", tags=["prompts"])


@router.get("/topics")
async def get_topics(
    url: str = Query(..., description="URL of the domain to analyze"),
    iso_code: Optional[str] = Query(
        None, description="ISO country code for geo-targeted results (e.g., US, GB, UA)"
    ),
    service: DataForSEOService = Depends(get_dataforseo_service),
):
    """
    Get topics/keywords relevant for a business and their industry.

    Args:
        url: The URL of the domain to analyze
        iso_code: Optional ISO country code for location-specific keywords
        service: DataForSEO service instance (injected)

    Returns:
        List of keywords sorted by search volume
    """
    # Validate and normalize the URL
    validated_url = await validate_and_normalize_url(url)

    # Map ISO code to location name if provided
    location_name = None
    if iso_code:
        location_name = get_location_name(iso_code.upper())
        if not location_name:
            raise HTTPException(
                status_code=400, detail=f"Invalid ISO country code: {iso_code}"
            )

    # Call DataForSEO service (injected singleton)
    keywords = await service.get_keywords_for_site(validated_url, location_name)

    return keywords
