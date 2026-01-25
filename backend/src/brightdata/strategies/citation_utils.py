"""Shared utilities for citation normalization across strategies."""

from typing import Any


def extract_index(raw_item: dict[str, Any]) -> int | None:
    """Extract index from webhook item (top-level or nested in 'input')."""
    if "index" in raw_item:
        return int(raw_item["index"])
    input_data = raw_item.get("input")
    if isinstance(input_data, dict) and "index" in input_data:
        return int(input_data["index"])
    return None


def normalize_citation(raw: dict[str, Any]) -> dict[str, str]:
    """Normalize a single citation to standard format."""
    return {
        "url": raw.get("url", ""),
        "text": raw.get("title", raw.get("text", raw.get("name", ""))),
        "domain": raw.get("domain", ""),
    }


def normalize_citations(raw_citations: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    """Normalize a list of citations."""
    if not raw_citations:
        return []
    return [normalize_citation(c) for c in raw_citations]


def merge_additional_sources(
    citations: list[dict[str, str]],
    additional: list[dict[str, Any]] | None,
) -> list[dict[str, str]]:
    """Merge additional sources (Perplexity 'sources', Gemini 'links_attached').

    Deduplicates by URL, preserves order.
    """
    if not additional:
        return citations
    existing_urls = {c["url"] for c in citations}
    result = list(citations)
    for item in additional:
        if isinstance(item, dict) and item.get("url") and item["url"] not in existing_urls:
            result.append(normalize_citation(item))
            existing_urls.add(item["url"])
    return result
