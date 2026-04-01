"""Service for fetching and parsing sitemap.xml files."""

import logging
import xml.etree.ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

_SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


class SitemapParser:
    """Fetches and parses sitemap.xml (including sitemap index files)."""

    def __init__(self, *, timeout: float = 15.0):
        self._timeout = timeout

    async def parse(self, sitemap_urls: list[str]) -> list[str]:
        """Return a flat, deduplicated list of page URLs from all provided sitemaps."""
        seen: set[str] = set()
        result: list[str] = []

        for url in sitemap_urls:
            pages = await self._fetch_and_parse(url, follow_index=True)
            for page in pages:
                if page not in seen:
                    seen.add(page)
                    result.append(page)

        return result

    async def _fetch_and_parse(self, url: str, *, follow_index: bool) -> list[str]:
        xml_text = await self._fetch(url)
        if xml_text is None:
            return []

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            logger.warning("Failed to parse XML from %s", url)
            return []

        tag = _strip_ns(root.tag)

        if tag == "sitemapindex" and follow_index:
            return await self._parse_sitemap_index(root)

        if tag == "urlset":
            return self._parse_urlset(root)

        logger.warning("Unknown root element <%s> in sitemap %s", tag, url)
        return []

    async def _parse_sitemap_index(self, root: ET.Element) -> list[str]:
        """Extract child sitemap URLs and fetch each (one level deep)."""
        child_urls: list[str] = []
        for sitemap_el in root.iter(f"{{{_SITEMAP_NS}}}sitemap"):
            loc = sitemap_el.findtext(f"{{{_SITEMAP_NS}}}loc")
            if loc:
                child_urls.append(loc.strip())

        # Also try without namespace (some sitemaps omit it)
        if not child_urls:
            for sitemap_el in root.iter("sitemap"):
                loc = sitemap_el.findtext("loc")
                if loc:
                    child_urls.append(loc.strip())

        pages: list[str] = []
        for child_url in child_urls:
            pages.extend(await self._fetch_and_parse(child_url, follow_index=False))
        return pages

    def _parse_urlset(self, root: ET.Element) -> list[str]:
        """Extract page URLs from a <urlset>."""
        urls: list[str] = []

        for url_el in root.iter(f"{{{_SITEMAP_NS}}}url"):
            loc = url_el.findtext(f"{{{_SITEMAP_NS}}}loc")
            if loc:
                urls.append(loc.strip())

        # Fallback: try without namespace
        if not urls:
            for url_el in root.iter("url"):
                loc = url_el.findtext("loc")
                if loc:
                    urls.append(loc.strip())

        return urls

    async def _fetch(self, url: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    url,
                    follow_redirects=True,
                    headers={"User-Agent": "GeoAuditBot/1.0"},
                )
                if response.status_code == 404:
                    logger.info("Sitemap not found at %s", url)
                    return None
                response.raise_for_status()
                return response.text
        except httpx.HTTPError:
            logger.warning("Failed to fetch sitemap from %s", url, exc_info=True)
            return None


def _strip_ns(tag: str) -> str:
    """Strip XML namespace prefix from a tag name."""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag
