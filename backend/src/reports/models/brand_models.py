"""Models for brand mention detection."""

from typing import List
from pydantic import BaseModel, Field


class BrandInputModel(BaseModel):
    """Brand specification for API request."""

    name: str = Field(..., description="Brand name")
    variations: List[str] = Field(
        ..., description="List of name variations to search for"
    )


class MentionPositionModel(BaseModel):
    """Position of a brand mention in text."""

    start: int = Field(..., description="Start character index")
    end: int = Field(..., description="End character index")
    matched_text: str = Field(..., description="The actual text that was matched")
    variation: str = Field(..., description="Which variation pattern matched")


class BrandMentionResultModel(BaseModel):
    """All mentions of a single brand."""

    brand_name: str = Field(..., description="Brand name")
    mentions: List[MentionPositionModel] = Field(
        ..., description="List of mention positions"
    )
