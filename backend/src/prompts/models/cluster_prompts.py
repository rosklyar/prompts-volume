"""Pydantic models for cluster-based prompt generation."""

from typing import List

from pydantic import BaseModel, Field


class ClusterPrompts(BaseModel):
    """Prompts generated for a specific keyword cluster."""

    cluster_id: int = Field(..., description="Cluster ID")
    keywords: List[str] = Field(..., description="Keywords from cluster used to generate prompts")
    prompts: List[str] = Field(..., description="E-commerce product search prompts for this cluster")


class TopicWithClusters(BaseModel):
    """Topic with associated cluster prompts.

    Note: Named 'TopicWithClusters' to avoid confusion with database Topic model.
    """

    topic: str = Field(..., description="Topic name")
    clusters: List[ClusterPrompts] = Field(..., description="List of cluster prompts for this topic")


class GeneratedPrompts(BaseModel):
    """Complete response with all topics and their cluster prompts."""

    topics: List[TopicWithClusters] = Field(..., description="List of topics with cluster prompts")
