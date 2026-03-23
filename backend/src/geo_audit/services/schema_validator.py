"""Service for validating detected structured data schemas."""

import re
from urllib.parse import urlparse

from src.geo_audit.constants import GOOGLE_RICH_RESULT_TYPES
from src.geo_audit.models.domain_models import DetectedSchema, ValidationIssue, ValidationResult

ISO_8601_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}"
    r"(T\d{2}:\d{2}(:\d{2})?"
    r"(Z|[+-]\d{2}:?\d{2})?)?$"
)

URL_PROPERTIES = {
    "url", "logo", "image", "sameAs", "mainEntityOfPage",
    "thumbnailUrl", "contentUrl", "embedUrl",
}

DATE_PROPERTIES = {
    "datePublished", "dateModified", "dateCreated",
    "startDate", "endDate", "uploadDate", "foundingDate",
}


class SchemaValidator:
    """Validates syntax and properties of detected schemas."""

    def validate(self, schemas: list[DetectedSchema]) -> ValidationResult:
        issues: list[ValidationIssue] = []
        valid = 0
        invalid = 0

        for schema in schemas:
            schema_issues = self._validate_schema(schema)
            if schema_issues:
                invalid += 1
                issues.extend(schema_issues)
            else:
                valid += 1

        return ValidationResult(issues=issues, valid_count=valid, invalid_count=invalid)

    def _validate_schema(self, schema: DetectedSchema) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if schema.format == "json-ld":
            issues.extend(self._validate_json_ld_structure(schema))

        issues.extend(self._validate_properties(schema))
        return issues

    def _validate_json_ld_structure(self, schema: DetectedSchema) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        props = schema.properties

        context = props.get("@context", "")
        if not context:
            issues.append(ValidationIssue(
                schema_type=schema.schema_type,
                severity="error",
                field="@context",
                message="Missing @context property",
            ))
        elif isinstance(context, str) and "schema.org" not in context:
            issues.append(ValidationIssue(
                schema_type=schema.schema_type,
                severity="warning",
                field="@context",
                message=f"Unexpected @context: {context}",
            ))

        if not props.get("@type"):
            issues.append(ValidationIssue(
                schema_type=schema.schema_type,
                severity="error",
                field="@type",
                message="Missing @type property",
            ))

        return issues

    def _validate_properties(self, schema: DetectedSchema) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        props = schema.properties

        # Check required properties for known rich result types
        rich_result = GOOGLE_RICH_RESULT_TYPES.get(schema.schema_type)
        if rich_result:
            for req_prop in rich_result.required_properties:
                if req_prop not in props:
                    issues.append(ValidationIssue(
                        schema_type=schema.schema_type,
                        severity="warning",
                        field=req_prop,
                        message=f"Missing required property '{req_prop}' for {schema.schema_type}",
                    ))

        # Validate URL properties
        for prop_name in URL_PROPERTIES:
            value = props.get(prop_name)
            if value is None:
                continue
            urls = value if isinstance(value, list) else [value]
            for url_val in urls:
                if isinstance(url_val, str) and url_val and not self._is_valid_url(url_val):
                    issues.append(ValidationIssue(
                        schema_type=schema.schema_type,
                        severity="warning",
                        field=prop_name,
                        message=f"URL property '{prop_name}' has invalid or relative URL: {url_val[:100]}",
                    ))

        # Validate date properties
        for prop_name in DATE_PROPERTIES:
            value = props.get(prop_name)
            if isinstance(value, str) and value and not ISO_8601_PATTERN.match(value):
                issues.append(ValidationIssue(
                    schema_type=schema.schema_type,
                    severity="warning",
                    field=prop_name,
                    message=f"Date property '{prop_name}' is not in ISO 8601 format: {value}",
                ))

        # Check author nesting — should be Person/Organization, not plain string
        author = props.get("author")
        if isinstance(author, str):
            issues.append(ValidationIssue(
                schema_type=schema.schema_type,
                severity="warning",
                field="author",
                message="'author' should be a Person or Organization object, not a plain string",
            ))

        # Check for empty/placeholder values
        for key, val in props.items():
            if key.startswith("@"):
                continue
            if isinstance(val, str) and val.strip() in ("", "null", "undefined", "TODO", "N/A"):
                issues.append(ValidationIssue(
                    schema_type=schema.schema_type,
                    severity="warning",
                    field=key,
                    message=f"Property '{key}' has empty or placeholder value",
                ))

        return issues

    def _is_valid_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except Exception:
            return False
