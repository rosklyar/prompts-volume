"""Service for computing the GEO audit score."""

from typing import Literal

from src.geo_audit.constants import ARTICLE_SUBTYPES, ORGANIZATION_SUBTYPES
from src.geo_audit.models.domain_models import (
    AuditScore,
    DeprecatedSchemaWarning,
    ExtractionResult,
    GeoReadinessResult,
    ScoreBreakdown,
    ValidationResult,
)


def _rating(total: float) -> Literal["Critical", "Poor", "Fair", "Good", "Excellent"]:
    if total <= 20:
        return "Critical"
    if total <= 40:
        return "Poor"
    if total <= 60:
        return "Fair"
    if total <= 80:
        return "Good"
    return "Excellent"


class AuditScorer:
    """Computes the weighted 0-100 GEO audit score per spec."""

    def score(
        self,
        *,
        extraction: ExtractionResult,
        validation: ValidationResult,
        geo_readiness: GeoReadinessResult,
        deprecated: list[DeprecatedSchemaWarning],
    ) -> AuditScore:
        breakdown: list[ScoreBreakdown] = [
            self._score_organization(extraction, geo_readiness),
            self._score_article(extraction, geo_readiness),
            self._score_person(extraction, geo_readiness),
            self._score_same_as(geo_readiness),
            self._score_speakable(geo_readiness),
            self._score_breadcrumb(extraction),
            self._score_website_search_action(geo_readiness),
            self._score_no_deprecated(deprecated),
            self._score_json_ld_format(extraction),
            self._score_validation(validation),
        ]

        total = min(sum(b.earned_points for b in breakdown), 100)

        return AuditScore(total=total, rating=_rating(total), breakdown=breakdown)

    def _signal(self, geo_readiness: GeoReadinessResult, name: str) -> float:
        """Get completeness for a named signal, 0.0 if not found."""
        for s in geo_readiness.signals:
            if s.name == name:
                return s.completeness if s.present else 0.0
        return 0.0

    def _score_organization(
        self, extraction: ExtractionResult, geo_readiness: GeoReadinessResult,
    ) -> ScoreBreakdown:
        # 20pts: present=10, sameAs to 3+ platforms=20
        max_pts = 20
        org_types = ORGANIZATION_SUBTYPES.intersection(set(extraction.schema_types_found))
        if not org_types:
            return ScoreBreakdown("organization", max_pts, 0)

        # Count sameAs links
        linked_count = sum(1 for link in geo_readiness.same_as_links if link.linked)
        if linked_count >= 3:
            return ScoreBreakdown("organization", max_pts, 20)
        return ScoreBreakdown("organization", max_pts, 10)

    def _score_article(
        self, extraction: ExtractionResult, geo_readiness: GeoReadinessResult,
    ) -> ScoreBreakdown:
        # 15pts: present=8, author as Person=12, dateModified=15
        max_pts = 15
        article_types = ARTICLE_SUBTYPES.intersection(set(extraction.schema_types_found))
        if not article_types:
            return ScoreBreakdown("article", max_pts, 0)

        # Find the article schema
        article = next(
            (s for s in extraction.schemas if s.schema_type in ARTICLE_SUBTYPES), None,
        )
        if not article:
            return ScoreBreakdown("article", max_pts, 0)

        author = article.properties.get("author")
        author_is_person = isinstance(author, dict) and author.get("@type") == "Person"
        has_date_modified = "dateModified" in article.properties

        if author_is_person and has_date_modified:
            return ScoreBreakdown("article", max_pts, 15)
        if author_is_person:
            return ScoreBreakdown("article", max_pts, 12)
        return ScoreBreakdown("article", max_pts, 8)

    def _score_person(
        self, extraction: ExtractionResult, geo_readiness: GeoReadinessResult,
    ) -> ScoreBreakdown:
        # 15pts: present=8, sameAs=12, jobTitle+knowsAbout=15
        max_pts = 15
        if "Person" not in extraction.schema_types_found:
            return ScoreBreakdown("person", max_pts, 0)

        person = next(
            (s for s in extraction.schemas if s.schema_type == "Person"), None,
        )
        if not person:
            return ScoreBreakdown("person", max_pts, 0)

        has_same_as = "sameAs" in person.properties
        has_job_title = "jobTitle" in person.properties
        has_knows_about = "knowsAbout" in person.properties

        if has_same_as and has_job_title and has_knows_about:
            return ScoreBreakdown("person", max_pts, 15)
        if has_same_as:
            return ScoreBreakdown("person", max_pts, 12)
        return ScoreBreakdown("person", max_pts, 8)

    def _score_same_as(self, geo_readiness: GeoReadinessResult) -> ScoreBreakdown:
        # 15pts: 1-2 platforms=5, 3-4=10, 5+ including Wikipedia=15
        max_pts = 15
        linked = [link for link in geo_readiness.same_as_links if link.linked]
        count = len(linked)
        has_wikipedia = any(link.platform == "wikipedia" for link in linked)

        if count >= 5 and has_wikipedia:
            return ScoreBreakdown("same_as", max_pts, 15)
        if count >= 3:
            return ScoreBreakdown("same_as", max_pts, 10)
        if count >= 1:
            return ScoreBreakdown("same_as", max_pts, 5)
        return ScoreBreakdown("same_as", max_pts, 0)

    def _score_speakable(self, geo_readiness: GeoReadinessResult) -> ScoreBreakdown:
        # 10pts: present and properly targeting content sections
        max_pts = 10
        completeness = self._signal(geo_readiness, "speakable")
        return ScoreBreakdown("speakable", max_pts, max_pts if completeness >= 0.5 else 0)

    def _score_breadcrumb(self, extraction: ExtractionResult) -> ScoreBreakdown:
        # 5pts: present and valid
        max_pts = 5
        if "BreadcrumbList" in extraction.schema_types_found:
            return ScoreBreakdown("breadcrumb", max_pts, 5)
        return ScoreBreakdown("breadcrumb", max_pts, 0)

    def _score_website_search_action(
        self, geo_readiness: GeoReadinessResult,
    ) -> ScoreBreakdown:
        # 5pts: present and valid
        max_pts = 5
        completeness = self._signal(geo_readiness, "WebSite+SearchAction")
        return ScoreBreakdown("website_search_action", max_pts, max_pts if completeness >= 0.5 else 0)

    def _score_no_deprecated(
        self, deprecated: list[DeprecatedSchemaWarning],
    ) -> ScoreBreakdown:
        # 5pts: no deprecated/removed schemas present
        max_pts = 5
        return ScoreBreakdown("no_deprecated", max_pts, 5 if not deprecated else 0)

    def _score_json_ld_format(self, extraction: ExtractionResult) -> ScoreBreakdown:
        # 5pts: all schemas in JSON-LD, not Microdata/RDFa
        max_pts = 5
        if not extraction.schemas:
            return ScoreBreakdown("json_ld_format", max_pts, 0)
        all_json_ld = all(s.format == "json-ld" for s in extraction.schemas)
        return ScoreBreakdown("json_ld_format", max_pts, 5 if all_json_ld else 0)

    def _score_validation(self, validation: ValidationResult) -> ScoreBreakdown:
        # 5pts: all schemas pass validation
        max_pts = 5
        has_errors = any(i.severity == "error" for i in validation.issues)
        return ScoreBreakdown("validation", max_pts, 5 if not has_errors else 0)
