"""Domain mention detection service."""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DomainInput:
    """Input domain specification (internal use)."""

    name: str
    domain: str
    is_brand: bool


@dataclass
class DomainMentionPosition:
    """Position of a domain mention in text."""

    start: int
    end: int
    matched_text: str
    matched_domain: str


@dataclass
class DomainMentionResult:
    """All mentions of a single domain in text."""

    name: str
    domain: str
    is_brand: bool
    mentions: List[DomainMentionPosition]


class DomainMentionDetector:
    """Detects domain mentions using regex-based matching."""

    def detect(
        self, text: str, domains: List[DomainInput]
    ) -> List[DomainMentionResult]:
        """
        Detect all domain mentions in the given text.

        Searches for domains including:
        - Bare domain: example.com
        - With www: www.example.com
        - With protocol: https://example.com
        - With subdomains: blog.example.com
        - With paths: example.com/products

        Args:
            text: The text to search for domain mentions
            domains: List of domains to search for

        Returns:
            List of DomainMentionResult, one per domain
        """
        if not text or not domains:
            return []

        results = []
        for domain_input in domains:
            if not domain_input.domain:
                continue

            mentions = self._find_domain_mentions(text, domain_input.domain)
            results.append(
                DomainMentionResult(
                    name=domain_input.name,
                    domain=domain_input.domain,
                    is_brand=domain_input.is_brand,
                    mentions=mentions,
                )
            )
        return results

    def _find_domain_mentions(
        self, text: str, domain: str
    ) -> List[DomainMentionPosition]:
        """Find all mentions of a domain in text."""
        mentions = []

        # Normalize domain (remove www. if present for matching)
        normalized_domain = domain.lower()
        if normalized_domain.startswith("www."):
            normalized_domain = normalized_domain[4:]

        # Escape special regex characters in domain
        escaped_domain = re.escape(normalized_domain)

        # Build pattern that matches:
        # - Word boundary or start (prevent matching inside larger words)
        # - Optional protocol (http:// or https://)
        # - Optional www.
        # - Optional subdomains (one or more like blog., api.v2., etc.)
        # - The exact domain
        # - Optional path, query string, fragment (until whitespace or end)
        #
        # Use lookbehind to ensure we don't match inside a word like "notexample.com"
        # The domain must be preceded by: start of string, whitespace, or subdomain dot
        pattern = (
            r"(?:(?<=\s)|(?<=^)|(?<=\.))"  # Must be after whitespace, start, or dot
            r"(?:https?://)?"  # Optional protocol
            r"(?:www\.)?"  # Optional www.
            r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)* "  # Optional subdomains
            + escaped_domain
            + r"(?:/[^\s<>\"'\]\)]*)?"  # Optional path
        )

        # Remove spaces from pattern (they were for readability)
        pattern = pattern.replace(" ", "")

        regex = re.compile(pattern, re.IGNORECASE)

        for match in regex.finditer(text):
            mentions.append(
                DomainMentionPosition(
                    start=match.start(),
                    end=match.end(),
                    matched_text=match.group(),
                    matched_domain=normalized_domain,
                )
            )

        # Sort by position for consistent ordering
        mentions.sort(key=lambda m: m.start)
        return mentions


def get_domain_mention_detector() -> DomainMentionDetector:
    """Dependency injection for DomainMentionDetector."""
    return DomainMentionDetector()
