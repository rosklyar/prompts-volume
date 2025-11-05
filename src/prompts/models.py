from typing import List
from pydantic import BaseModel, Field


class Topic(BaseModel):
    topic: str = Field(..., description="Topic")
    prompts: List[str] = Field(..., description="List of prompts for this topic")


class GeneratedPrompts(BaseModel):
    topics: List[Topic] = Field(..., description="List of topics with prompts")
