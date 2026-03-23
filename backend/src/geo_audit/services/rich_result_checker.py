"""Service for checking Google rich result eligibility."""

from src.geo_audit.constants import GOOGLE_RICH_RESULT_TYPES
from src.geo_audit.models.domain_models import DetectedSchema, RichResultCheckResult, RichResultGap


class RichResultChecker:
    """Compares detected schemas against Google's rich result requirements."""

    def check(self, schemas: list[DetectedSchema]) -> RichResultCheckResult:
        detected_types = {s.schema_type for s in schemas}
        schema_by_type: dict[str, DetectedSchema] = {}
        for s in schemas:
            if s.schema_type not in schema_by_type:
                schema_by_type[s.schema_type] = s

        eligible: list[str] = []
        gaps: list[RichResultGap] = []

        for schema_type, rich_result in GOOGLE_RICH_RESULT_TYPES.items():
            if schema_type not in detected_types:
                continue

            schema = schema_by_type[schema_type]
            missing_required = [
                p for p in rich_result.required_properties
                if p not in schema.properties
            ]
            missing_recommended = [
                p for p in rich_result.recommended_properties
                if p not in schema.properties
            ]

            if not missing_required:
                eligible.append(schema_type)
                if missing_recommended:
                    gaps.append(RichResultGap(
                        schema_type=schema_type,
                        status="incomplete",
                        missing_required=[],
                        missing_recommended=missing_recommended,
                    ))
            else:
                gaps.append(RichResultGap(
                    schema_type=schema_type,
                    status="incomplete",
                    missing_required=missing_required,
                    missing_recommended=missing_recommended,
                ))

        return RichResultCheckResult(eligible=eligible, gaps=gaps)
