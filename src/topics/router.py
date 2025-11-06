"""Router for topics-related endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.config.countries import Country, get_country_by_code
from src.topics.service import DataForSEOService, get_dataforseo_service
from src.utils.url_validator import validate_url, extract_domain

router = APIRouter(prefix="/prompts/api/v1", tags=["topics"])


def _validate_and_get_country(iso_code: Optional[str]) -> Optional[Country]:
    """
    Validate ISO country code and return corresponding Country object.

    Args:
        iso_code: Optional ISO country code (e.g., 'US', 'GB', 'ua')

    Returns:
        Country object if valid ISO code provided, None if no iso_code

    Raises:
        HTTPException: If ISO code is invalid (400 error)
    """
    if not iso_code:
        return None

    country = get_country_by_code(iso_code.upper())
    if not country:
        raise HTTPException(
            status_code=400, detail=f"Invalid ISO country code: {iso_code}"
        )

    return country


@router.get("/topics", response_model=List[str])
async def get_topics(
    url: str = Query(..., description="URL of the domain to analyze"),
    iso_code: str = Query(
        None, description="ISO country code for geo-targeted results (e.g., US, GB, UA)"
    ),
    service: DataForSEOService = Depends(get_dataforseo_service),
):
    """
    Get topics/keywords where the domain currently ranks in organic search.

    Uses DataForSEO Labs Ranked Keywords API to find keywords where the domain
    has organic search visibility. The first preferred language of the country
    is used for language-specific results.

    Args:
        url: The URL of the domain to analyze
        iso_code: Optional ISO country code for location-specific keywords and language
        service: DataForSEO service instance (injected)

    Returns:
        List of keywords where the domain ranks in organic search
    """
    # Validate and normalize the URL
    domain = extract_domain(await validate_url(url))

    # Validate ISO code and get country
    country = _validate_and_get_country(iso_code)

    # Call DataForSEO service with bare domain, location, and language
    keywords = await service.get_keywords_for_site(
        domain, country.name, country.preferred_languages[0].name
    )

    return keywords
