"""Service for matching GSC properties to brand domains."""

from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

from src.gsc.models import GSCSiteInfo


@dataclass(frozen=True)
class PropertyMatch:
    """Result of property matching.

    Attributes:
        match_type: Type of match found
        matched_property: The matched site URL (if single match)
        available_properties: All available properties for selection
    """

    match_type: Literal["exact", "partial", "multiple", "none"]
    matched_property: str | None
    available_properties: list[GSCSiteInfo]


class PropertyMatcher:
    """Matches a brand domain to GSC properties.

    Supports two GSC property formats:
    - Domain property: "sc-domain:example.com"
    - URL prefix: "https://example.com/" or "http://example.com/"
    """

    def match(
        self,
        brand_domain: str,
        properties: list[GSCSiteInfo],
    ) -> PropertyMatch:
        """Match brand domain to GSC properties.

        Args:
            brand_domain: The brand's domain (e.g., "example.com" or "www.example.com")
            properties: List of GSC properties the user has access to

        Returns:
            PropertyMatch with match type and matched property if found
        """
        if not properties:
            return PropertyMatch(
                match_type="none",
                matched_property=None,
                available_properties=[],
            )

        normalized_domain = self._normalize_domain(brand_domain)
        exact_matches: list[GSCSiteInfo] = []
        partial_matches: list[GSCSiteInfo] = []

        for prop in properties:
            prop_domain = self._extract_domain_from_property(prop.site_url)

            if prop_domain == normalized_domain:
                exact_matches.append(prop)
            elif self._is_partial_match(normalized_domain, prop_domain):
                partial_matches.append(prop)

        # Exact match(es)
        if len(exact_matches) == 1:
            return PropertyMatch(
                match_type="exact",
                matched_property=exact_matches[0].site_url,
                available_properties=properties,
            )
        if len(exact_matches) > 1:
            return PropertyMatch(
                match_type="multiple",
                matched_property=None,
                available_properties=properties,
            )

        # Partial match(es)
        if len(partial_matches) == 1:
            return PropertyMatch(
                match_type="partial",
                matched_property=partial_matches[0].site_url,
                available_properties=properties,
            )
        if len(partial_matches) > 1:
            return PropertyMatch(
                match_type="multiple",
                matched_property=None,
                available_properties=properties,
            )

        # No match
        return PropertyMatch(
            match_type="none",
            matched_property=None,
            available_properties=properties,
        )

    def _normalize_domain(self, domain: str) -> str:
        """Normalize domain by removing protocol, www prefix, and trailing slashes."""
        domain = domain.lower().strip()

        # Remove protocol if present
        if domain.startswith("http://") or domain.startswith("https://"):
            parsed = urlparse(domain)
            domain = parsed.netloc

        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]

        # Remove trailing slashes
        domain = domain.rstrip("/")

        return domain

    def _extract_domain_from_property(self, site_url: str) -> str:
        """Extract normalized domain from GSC property URL.

        Handles both formats:
        - "sc-domain:example.com"
        - "https://example.com/"
        """
        if site_url.startswith("sc-domain:"):
            # Domain property format
            domain = site_url[10:]  # Remove "sc-domain:" prefix
            return self._normalize_domain(domain)

        # URL prefix format
        parsed = urlparse(site_url)
        domain = parsed.netloc

        return self._normalize_domain(domain)

    def _is_partial_match(self, brand_domain: str, property_domain: str) -> bool:
        """Check if domains partially match.

        A partial match occurs when:
        - Brand domain is a subdomain of property domain
        - Property domain is a subdomain of brand domain
        - One contains the other as a suffix
        """
        if not brand_domain or not property_domain:
            return False

        # Check if one is a subdomain of the other
        if brand_domain.endswith("." + property_domain):
            return True
        if property_domain.endswith("." + brand_domain):
            return True

        return False
