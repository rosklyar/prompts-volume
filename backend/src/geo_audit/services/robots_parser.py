"""Service for fetching and parsing robots.txt."""

import logging
from urllib.parse import urljoin

import httpx

from src.geo_audit.models.domain_models import RobotsResult

logger = logging.getLogger(__name__)

USER_AGENT = "GeoAuditBot"
_DEFAULT_CRAWL_DELAY = 0.2


class RobotsParser:
    """Fetches and parses robots.txt for sitemap URLs, disallow rules, and crawl-delay."""

    def __init__(self, *, timeout: float = 10.0, default_crawl_delay: float = _DEFAULT_CRAWL_DELAY):
        self._timeout = timeout
        self._default_crawl_delay = default_crawl_delay

    async def parse(self, base_url: str) -> RobotsResult:
        """Fetch robots.txt and extract relevant directives.

        Returns a default RobotsResult if robots.txt is missing or unparseable.
        """
        robots_url = urljoin(base_url.rstrip("/") + "/", "robots.txt")
        text = await self._fetch(robots_url)
        if text is None:
            return RobotsResult(crawl_delay=self._default_crawl_delay)
        return self._parse_text(text)

    async def _fetch(self, url: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    url,
                    follow_redirects=True,
                    headers={"User-Agent": f"{USER_AGENT}/1.0"},
                )
                if response.status_code == 404:
                    logger.info("robots.txt not found at %s", url)
                    return None
                response.raise_for_status()
                return response.text
        except httpx.HTTPError:
            logger.warning("Failed to fetch robots.txt from %s", url, exc_info=True)
            return None

    def _parse_text(self, text: str) -> RobotsResult:
        sitemap_urls: list[str] = []
        disallow_rules: list[str] = []
        crawl_delay: float | None = None

        current_agent_applies = False

        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue

            if ":" not in line:
                continue

            directive, _, value = line.partition(":")
            directive = directive.strip().lower()
            value = value.strip()

            if directive == "sitemap":
                if value:
                    sitemap_urls.append(value)
                continue

            if directive == "user-agent":
                agent = value.lower()
                current_agent_applies = agent == "*" or USER_AGENT.lower() in agent
                continue

            if not current_agent_applies:
                continue

            if directive == "disallow" and value:
                disallow_rules.append(value)
            elif directive == "crawl-delay" and value:
                try:
                    crawl_delay = float(value)
                except ValueError:
                    pass

        return RobotsResult(
            sitemap_urls=sitemap_urls,
            disallow_rules=disallow_rules,
            crawl_delay=crawl_delay if crawl_delay is not None else self._default_crawl_delay,
        )
