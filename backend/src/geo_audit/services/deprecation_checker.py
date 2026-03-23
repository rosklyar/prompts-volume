"""Service for flagging deprecated schema types."""

from src.geo_audit.constants import DEPRECATED_SCHEMAS
from src.geo_audit.models.domain_models import DetectedSchema, DeprecatedSchemaWarning


class DeprecationChecker:
    """Flags deprecated or removed schema types."""

    def check(self, schemas: list[DetectedSchema]) -> list[DeprecatedSchemaWarning]:
        warnings: list[DeprecatedSchemaWarning] = []
        seen: set[str] = set()

        for schema in schemas:
            if schema.schema_type in seen:
                continue
            deprecated = DEPRECATED_SCHEMAS.get(schema.schema_type)
            if deprecated:
                seen.add(schema.schema_type)
                warnings.append(DeprecatedSchemaWarning(
                    schema_type=deprecated.schema_type,
                    status=deprecated.status,
                    message=deprecated.message,
                ))

        return warnings
