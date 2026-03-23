"""Service for extracting structured data from HTML."""

import json
import logging

from bs4 import BeautifulSoup, Tag

from src.geo_audit.models.domain_models import DetectedSchema, ExtractionResult

logger = logging.getLogger(__name__)


class StructuredDataExtractor:
    """Extracts JSON-LD, Microdata, and RDFa from HTML."""

    def extract(self, html: str) -> ExtractionResult:
        soup = BeautifulSoup(html, "html.parser")
        schemas: list[DetectedSchema] = []

        schemas.extend(self._extract_json_ld(soup))
        schemas.extend(self._extract_microdata(soup))
        schemas.extend(self._extract_rdfa(soup))

        formats_found = sorted(set(s.format for s in schemas))
        types_found = sorted(set(s.schema_type for s in schemas))

        return ExtractionResult(
            schemas=schemas,
            total_blocks=len(schemas),
            formats_found=formats_found,
            schema_types_found=types_found,
        )

    def _extract_json_ld(self, soup: BeautifulSoup) -> list[DetectedSchema]:
        schemas: list[DetectedSchema] = []
        for script in soup.find_all("script", type="application/ld+json"):
            raw = script.string
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Malformed JSON-LD block skipped")
                continue

            for item in self._flatten_json_ld(data):
                schema_type = item.get("@type", "Unknown")
                if isinstance(schema_type, list):
                    schema_type = schema_type[0] if schema_type else "Unknown"
                schemas.append(DetectedSchema(
                    format="json-ld",
                    schema_type=schema_type,
                    raw_content=json.dumps(item, ensure_ascii=False),
                    properties=item,
                ))
        return schemas

    def _flatten_json_ld(self, data: dict | list) -> list[dict]:
        """Flatten @graph arrays and top-level arrays into individual items."""
        if isinstance(data, list):
            items: list[dict] = []
            for entry in data:
                if isinstance(entry, dict):
                    items.extend(self._flatten_json_ld(entry))
            return items

        if isinstance(data, dict):
            if "@graph" in data:
                return self._flatten_json_ld(data["@graph"])
            return [data]

        return []

    def _extract_microdata(self, soup: BeautifulSoup) -> list[DetectedSchema]:
        schemas: list[DetectedSchema] = []
        for element in soup.find_all(attrs={"itemscope": True}):
            if not isinstance(element, Tag):
                continue
            # Skip nested itemscopes (they'll be picked up as properties)
            if element.find_parent(attrs={"itemscope": True}):
                continue

            itemtype = element.get("itemtype", "")
            if isinstance(itemtype, list):
                itemtype = itemtype[0] if itemtype else ""
            schema_type = str(itemtype).rsplit("/", 1)[-1] if itemtype else "Unknown"

            properties = self._extract_microdata_properties(element)
            schemas.append(DetectedSchema(
                format="microdata",
                schema_type=schema_type,
                raw_content=str(element)[:500],
                properties=properties,
            ))
        return schemas

    def _extract_microdata_properties(self, element: Tag) -> dict:
        props: dict = {}
        for child in element.find_all(attrs={"itemprop": True}):
            if not isinstance(child, Tag):
                continue
            prop_name = child.get("itemprop", "")
            if isinstance(prop_name, list):
                prop_name = prop_name[0] if prop_name else ""

            if child.has_attr("itemscope"):
                nested_type = str(child.get("itemtype", "")).rsplit("/", 1)[-1]
                value = {
                    "@type": nested_type,
                    **self._extract_microdata_properties(child),
                }
            elif child.has_attr("content"):
                value = child["content"]
            elif child.has_attr("href"):
                value = child["href"]
            elif child.has_attr("src"):
                value = child["src"]
            else:
                value = child.get_text(strip=True)

            if prop_name in props:
                existing = props[prop_name]
                if isinstance(existing, list):
                    existing.append(value)
                else:
                    props[prop_name] = [existing, value]
            else:
                props[prop_name] = value
        return props

    def _extract_rdfa(self, soup: BeautifulSoup) -> list[DetectedSchema]:
        schemas: list[DetectedSchema] = []
        for element in soup.find_all(attrs={"typeof": True}):
            if not isinstance(element, Tag):
                continue
            typeof = element.get("typeof", "")
            if isinstance(typeof, list):
                typeof = typeof[0] if typeof else ""
            schema_type = str(typeof).rsplit("/", 1)[-1].rsplit(":", 1)[-1] if typeof else "Unknown"

            properties: dict = {}
            for prop_el in element.find_all(attrs={"property": True}):
                if not isinstance(prop_el, Tag):
                    continue
                prop_name = str(prop_el.get("property", "")).rsplit(":", 1)[-1]
                value = (
                    prop_el.get("content")
                    or prop_el.get("href")
                    or prop_el.get_text(strip=True)
                )
                properties[prop_name] = value

            schemas.append(DetectedSchema(
                format="rdfa",
                schema_type=schema_type,
                raw_content=str(element)[:500],
                properties=properties,
            ))
        return schemas
