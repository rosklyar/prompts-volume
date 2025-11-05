"""Router for prompts generation endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.prompts.models import GeneratedPrompts
from src.prompts.service import PromptsGeneratorService, get_prompts_generator_service

router = APIRouter(prefix="/prompts/api/v1", tags=["prompts"])


class GeneratePromptsRequest(BaseModel):
    """Request model for generating prompts."""

    topics: List[str] = Field(
        ..., description="List of topics to generate prompts for", min_length=1
    )
    brand_name: str = Field(..., description="Company brand name")
    business_domain: str = Field(..., description="Business domain/industry")
    country: str = Field(..., description="Target country")
    language: str = Field(..., description="Target language for prompts")
    business_description: str = Field(..., description="Detailed business description")
    prompts_per_topic: int = Field(
        default=10,
        description="Number of prompts to generate per topic",
        ge=1,
        le=50,
    )


@router.post("/generate", response_model=GeneratedPrompts)
async def generate_prompts(
    request: GeneratePromptsRequest,
    service: PromptsGeneratorService = Depends(get_prompts_generator_service),
):
    """
    Generate customer search prompts based on business information and topics.

    This endpoint uses OpenAI to generate natural, customer-focused search prompts
    that businesses can use to understand how potential customers might search for
    their products/services.

    Args:
        request: Request containing topics and business information
        service: PromptsGeneratorService instance (injected)

    Returns:
        GeneratedPrompts object with topics and their prompts

    Raises:
        HTTPException: If generation fails or validation errors occur
    """
    try:
        result = await service.generate_prompts(
            topics=request.topics,
            brand_name=request.brand_name,
            business_domain=request.business_domain,
            country=request.country,
            language=request.language,
            business_description=request.business_description,
            prompts_per_topic=request.prompts_per_topic,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate prompts: {str(e)}"
        )
