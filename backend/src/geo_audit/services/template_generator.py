"""Service for generating JSON-LD templates using OpenAI."""

import json
import logging

from openai import AsyncOpenAI

from src.geo_audit.models.domain_models import (
    ExtractionResult,
    GeneratedTemplate,
    GeoReadinessResult,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a schema markup specialist. Generate JSON-LD templates for missing \
structured data schemas on a website.

Rules:
- Use JSON-LD format exclusively with @context: "https://schema.org"
- Use placeholder values marked as [REPLACE: description of what goes here]
- Include all required properties for Google rich result eligibility
- Include all recommended properties for GEO optimization
- Each template must be syntactically valid JSON
- Focus on schemas critical for AI discoverability

Return a JSON array of objects, each with:
- "schema_type": the Schema.org type
- "json_ld": the complete JSON-LD template as a string
- "rationale": why this template is recommended (1-2 sentences)

Return ONLY the JSON array, no markdown formatting."""


class TemplateGenerator:
    """Generates contextual JSON-LD templates for missing schemas via OpenAI."""

    def __init__(self, *, api_key: str | None, model: str):
        if api_key:
            self._client: AsyncOpenAI | None = AsyncOpenAI(api_key=api_key)
        else:
            self._client = None
            logger.warning("No OpenAI API key — template generation disabled")
        self._model = model

    async def generate(
        self,
        *,
        url: str,
        extraction: ExtractionResult,
        geo_readiness: GeoReadinessResult,
    ) -> list[GeneratedTemplate]:
        if self._client is None:
            return []

        missing_types = self._identify_missing_types(extraction, geo_readiness)
        if not missing_types:
            return []

        prompt = self._build_prompt(url, missing_types, extraction)
        try:
            response = await self._client.responses.create(
                model=self._model,
                input=prompt,
                instructions=_SYSTEM_PROMPT,
            )
            return self._parse_templates(response.output_text)
        except Exception:
            logger.exception("Template generation failed")
            return []

    def _identify_missing_types(
        self, extraction: ExtractionResult, geo_readiness: GeoReadinessResult,
    ) -> list[str]:
        existing = set(extraction.schema_types_found)
        missing: list[str] = []

        # Always recommend these if missing
        geo_type_map = {
            "Organization": {"Organization", "LocalBusiness", "Corporation"},
            "Person": {"Person"},
            "Article": {"Article", "BlogPosting", "NewsArticle"},
            "BreadcrumbList": {"BreadcrumbList"},
            "WebSite": {"WebSite"},
        }

        for label, type_set in geo_type_map.items():
            if not type_set.intersection(existing):
                missing.append(label)

        # Check speakable on existing article schemas
        speakable_signal = next(
            (s for s in geo_readiness.signals if s.name == "speakable"), None,
        )
        if speakable_signal and not speakable_signal.present:
            missing.append("speakable (add to Article schema)")

        return missing

    def _build_prompt(
        self, url: str, missing_types: list[str], extraction: ExtractionResult,
    ) -> str:
        existing_summary = ", ".join(extraction.schema_types_found) if extraction.schema_types_found else "none"

        return (
            f"Website URL: {url}\n"
            f"Existing schemas found: {existing_summary}\n"
            f"Missing schemas to generate templates for: {', '.join(missing_types)}\n\n"
            "Generate JSON-LD templates for each missing schema type listed above. "
            "Customize the templates for the website context (use the URL to infer "
            "the likely business type and content). For Organization, include a "
            "comprehensive sameAs array with placeholders for Wikipedia, Wikidata, "
            "LinkedIn, YouTube, Crunchbase, Twitter/X, Facebook, and GitHub. "
            "For Article schemas, include the speakable property with cssSelector."
        )

    def _parse_templates(self, response_text: str) -> list[GeneratedTemplate]:
        content = self._extract_json(response_text)
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.error("Failed to parse template generation response as JSON")
            return []

        if not isinstance(data, list):
            data = [data]

        templates: list[GeneratedTemplate] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            schema_type = item.get("schema_type", "Unknown")
            json_ld = item.get("json_ld", "")
            if isinstance(json_ld, dict):
                json_ld = json.dumps(json_ld, indent=2, ensure_ascii=False)
            rationale = item.get("rationale", "")
            templates.append(GeneratedTemplate(
                schema_type=schema_type,
                json_ld=json_ld,
                rationale=rationale,
            ))

        return templates

    def _extract_json(self, content: str) -> str:
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()
