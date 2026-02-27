"""Pydantic request/response models for keyword inspiration API."""

from pydantic import BaseModel, Field

from src.prompt_groups.models.brand_models import BrandModel, CompetitorModel


# --- Step 1: Discover clusters (fetch + cluster combined) ---


class DiscoverClustersRequest(BaseModel):
    domains: list[str] = Field(..., min_length=1)
    country_code: str = Field(..., min_length=2, max_length=10)
    language_name: str = Field(..., min_length=1, max_length=100)
    brand_names: list[str] = Field(default_factory=list)


class ScoredClusterResponse(BaseModel):
    cluster_id: int
    keywords: list[str]
    score: float
    title: str
    keyword_count: int


class ClusterKeywordsResponse(BaseModel):
    clusters: list[ScoredClusterResponse]
    total_keywords: int
    noise_keywords: int


# --- Step 2: Generate prompts preview (no DB writes) ---


class ClusterSelection(BaseModel):
    cluster_id: int
    keywords: list[str]
    title: str


class GeneratePromptsRequest(BaseModel):
    clusters: list[ClusterSelection] = Field(..., min_length=1)
    business_domain: str
    language: str


class GeneratedPromptItem(BaseModel):
    prompt_text: str
    source_keyword: str


class ClusterPrompts(BaseModel):
    cluster_id: int
    title: str
    prompts: list[GeneratedPromptItem]


class GeneratePromptsResponse(BaseModel):
    clusters: list[ClusterPrompts]
    total_prompts: int


# --- Step 3: Confirm selection and create groups ---


class ConfirmedCluster(BaseModel):
    title: str
    prompts: list[str]  # only user-selected prompt texts


class ConfirmGroupsRequest(BaseModel):
    clusters: list[ConfirmedCluster] = Field(..., min_length=1)
    country_id: int
    brand: BrandModel
    competitors: list[CompetitorModel] | None = None


class CreatedGroupInfo(BaseModel):
    group_id: int
    title: str
    prompts_count: int


class CreateGroupsResponse(BaseModel):
    groups: list[CreatedGroupInfo]
    total_prompts: int
