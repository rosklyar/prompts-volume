"""Service for discovering pages via sitemap + BFS crawl."""

import asyncio
import logging
from collections import deque
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from src.geo_audit.models.domain_models import PageDiscoveryResult, RobotsResult
from src.geo_audit.services.robots_parser import RobotsParser
from src.geo_audit.services.sitemap_parser import SitemapParser

logger = logging.getLogger(__name__)


class PageDiscoverer:
    """Discovers pages via sitemap + BFS crawl, respecting robots.txt."""

    def __init__(
        self,
        *,
        robots_parser: RobotsParser,
        sitemap_parser: SitemapParser,
        max_pages: int = 25,
        max_concurrent: int = 5,
        fetch_timeout: float = 10.0,
    ):
        self._robots_parser = robots_parser
        self._sitemap_parser = sitemap_parser
        self._max_pages = max_pages
        self._max_concurrent = max_concurrent
        self._fetch_timeout = fetch_timeout

    async def discover(self, base_url: str) -> PageDiscoveryResult:
        """Return an ordered list of up to max_pages URLs to audit.

        Priority: homepage first, then sitemap pages, then BFS-crawled pages.
        Respects robots.txt Disallow rules and crawl-delay.
        """
        base_url = base_url.rstrip("/")
        base_domain = urlparse(base_url).netloc.lower()

        # Step 1: Parse robots.txt
        robots = await self._robots_parser.parse(base_url)

        # Step 2: Parse sitemaps
        sitemap_urls = await self._sitemap_parser.parse(robots.sitemap_urls)

        # Step 3: Filter sitemap pages
        sitemap_pages = [
            url for url in sitemap_urls
            if self._is_same_domain(url, base_domain) and not self._is_disallowed(url, robots)
        ]

        # Step 4: Build ordered URL list (homepage first)
        homepage = base_url + "/"
        urls: list[str] = [homepage]
        seen: set[str] = {self._normalize(homepage)}

        # Add sitemap pages
        for url in sitemap_pages:
            normalized = self._normalize(url)
            if normalized not in seen and len(urls) < self._max_pages:
                seen.add(normalized)
                urls.append(url)

        sitemap_page_count = len(urls) - 1  # exclude homepage

        # Step 5: BFS crawl if we need more pages
        crawled_count = 0
        if len(urls) < self._max_pages:
            crawled_count = await self._bfs_crawl(
                base_url=base_url,
                base_domain=base_domain,
                robots=robots,
                urls=urls,
                seen=seen,
            )

        return PageDiscoveryResult(
            urls=urls,
            robots=robots,
            sitemap_page_count=sitemap_page_count,
            crawled_page_count=crawled_count,
        )

    async def _bfs_crawl(
        self,
        *,
        base_url: str,
        base_domain: str,
        robots: RobotsResult,
        urls: list[str],
        seen: set[str],
    ) -> int:
        """BFS-crawl pages starting from already-known URLs, extracting internal links."""
        queue: deque[str] = deque(urls[:])  # start from all known pages
        semaphore = asyncio.Semaphore(self._max_concurrent)
        crawled_count = 0

        while queue and len(urls) < self._max_pages:
            # Process a batch from the queue
            batch_size = min(len(queue), self._max_concurrent, self._max_pages - len(urls) + len(queue))
            batch = [queue.popleft() for _ in range(min(batch_size, len(queue) + 1)) if queue]

            tasks = [self._fetch_and_extract_links(url, semaphore) for url in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, BaseException):
                    continue

                for link in result:
                    if len(urls) >= self._max_pages:
                        break
                    normalized = self._normalize(link)
                    if normalized in seen:
                        continue
                    if not self._is_same_domain(link, base_domain):
                        continue
                    if self._is_disallowed(link, robots):
                        continue
                    seen.add(normalized)
                    urls.append(link)
                    queue.append(link)
                    crawled_count += 1

            # Respect crawl-delay between batches
            if queue and len(urls) < self._max_pages:
                await asyncio.sleep(robots.crawl_delay)

        return crawled_count

    async def _fetch_and_extract_links(self, url: str, semaphore: asyncio.Semaphore) -> list[str]:
        """Fetch a page and extract internal <a href> links."""
        async with semaphore:
            try:
                async with httpx.AsyncClient(timeout=self._fetch_timeout) as client:
                    response = await client.get(
                        url,
                        follow_redirects=True,
                        headers={"User-Agent": "GeoAuditBot/1.0"},
                    )
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "")
                    if "text/html" not in content_type:
                        return []
                    return self._extract_links(response.text, url)
            except httpx.HTTPError:
                logger.debug("Failed to fetch %s during BFS crawl", url)
                return []

    def _extract_links(self, html: str, page_url: str) -> list[str]:
        """Extract unique absolute internal links from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []
        seen_in_page: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue

            absolute = urljoin(page_url, href)
            # Strip fragment
            parsed = urlparse(absolute)
            clean = parsed._replace(fragment="").geturl()

            if clean not in seen_in_page:
                seen_in_page.add(clean)
                links.append(clean)

        return links

    def _is_same_domain(self, url: str, base_domain: str) -> bool:
        parsed = urlparse(url)
        return parsed.netloc.lower() == base_domain

    def _is_disallowed(self, url: str, robots: RobotsResult) -> bool:
        path = urlparse(url).path
        return any(path.startswith(rule) for rule in robots.disallow_rules)

    def _normalize(self, url: str) -> str:
        """Normalize URL for deduplication (lowercase scheme+host, strip trailing slash + fragment)."""
        parsed = urlparse(url)
        path = parsed.path.rstrip("/") or "/"
        return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"
