"""Pydantic models for generate prompts request."""

from typing import List

from pydantic import BaseModel, Field


class GeneratePromptsRequest(BaseModel):
    """Request model for generate prompts endpoint."""

    company_url: str = Field(
        ..., description="Company website URL (e.g., 'moyo.ua', 'https://example.com')"
    )
    iso_country_code: str = Field(
        ..., description="ISO 3166-1 alpha-2 country code (e.g., 'UA', 'US')"
    )
    topics: List[str] = Field(
        ..., min_length=1, description="Selected topics from /meta-info endpoint"
    )
    brand_variations: List[str] = Field(
        ..., min_length=1, description="Selected brand variations from /meta-info endpoint"
    )
