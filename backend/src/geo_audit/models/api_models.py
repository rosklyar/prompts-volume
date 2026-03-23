"""Pydantic request/response models for GEO schema audit."""

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class GeoAuditRequest(BaseModel):
    url: HttpUrl | None = Field(None, description="URL to audit. If omitted, uses brand domain from preferences.")


class DetectedSchemaResponse(BaseModel):
    format: str
    schema_type: str
    properties: dict


class ExtractionResponse(BaseModel):
    total_blocks: int
    formats_found: list[str]
    schema_types_found: list[str]
    schemas: list[DetectedSchemaResponse]


class ValidationIssueResponse(BaseModel):
    schema_type: str
    severity: str
    field: str | None
    message: str


class ValidationResponse(BaseModel):
    valid_count: int
    invalid_count: int
    issues: list[ValidationIssueResponse]


class RichResultGapResponse(BaseModel):
    schema_type: str
    status: str
    missing_required: list[str]
    missing_recommended: list[str]


class RichResultCheckResponse(BaseModel):
    eligible: list[str]
    gaps: list[RichResultGapResponse]


class GeoSignalResponse(BaseModel):
    name: str
    present: bool
    completeness: float
    details: str


class SameAsLinkResponse(BaseModel):
    platform: str
    linked: bool
    url: str | None


class GeoReadinessResponse(BaseModel):
    signals: list[GeoSignalResponse]
    same_as_links: list[SameAsLinkResponse]
    overall_readiness: float


class DeprecatedSchemaResponse(BaseModel):
    schema_type: str
    status: str
    message: str


class JsRenderingWarningResponse(BaseModel):
    framework: str
    confidence: str
    message: str


class GeneratedTemplateResponse(BaseModel):
    schema_type: str
    json_ld: str
    rationale: str


class ScoreBreakdownResponse(BaseModel):
    component: str
    max_points: float
    earned_points: float


class AuditScoreResponse(BaseModel):
    total: float
    rating: str
    breakdown: list[ScoreBreakdownResponse]


class GeoAuditResponse(BaseModel):
    url: str
    extraction: ExtractionResponse
    validation: ValidationResponse
    rich_results: RichResultCheckResponse
    geo_readiness: GeoReadinessResponse
    deprecated_schemas: list[DeprecatedSchemaResponse]
    js_rendering_warnings: list[JsRenderingWarningResponse]
    recommended_templates: list[GeneratedTemplateResponse]
    score: AuditScoreResponse


class GeoAuditStoredResponse(BaseModel):
    id: int
    url: str
    score_total: float
    score_rating: str
    result: GeoAuditResponse
    created_at: datetime
