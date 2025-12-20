"""Unit tests for CitationLeaderboardBuilder service."""

import pytest

from src.evaluations.services.citation_leaderboard_builder import (
    CitationInput,
    CitationLeaderboardBuilder,
)


class TestCitationLeaderboardBuilder:
    """Tests for CitationLeaderboardBuilder."""

    def setup_method(self):
        """Set up test fixtures."""
        self.builder = CitationLeaderboardBuilder(max_path_depth=2)

    def test_aggregate_single_domain(self):
        """Test aggregating citations from a single domain."""
        citations = [
            CitationInput(url="https://rozetka.com.ua/phones/123", text="Phone 1"),
            CitationInput(url="https://rozetka.com.ua/phones/456", text="Phone 2"),
        ]

        result = self.builder.aggregate(citations)

        assert result.total_citations == 2

        # Find domain-level item
        domain_items = [i for i in result.items if i.is_domain]
        assert len(domain_items) == 1
        assert domain_items[0].path == "rozetka.com.ua"
        assert domain_items[0].count == 2

    def test_aggregate_multiple_path_levels(self):
        """Test aggregation at multiple path levels."""
        citations = [
            CitationInput(
                url="https://rozetka.com.ua/ua/mobile-phones/xyz", text=""
            ),
        ]

        result = self.builder.aggregate(citations)

        paths = [item.path for item in result.items]
        assert "rozetka.com.ua" in paths
        assert "rozetka.com.ua/ua" in paths
        assert "rozetka.com.ua/ua/mobile-phones" in paths

    def test_aggregate_path_frequency(self):
        """Test that sub-paths are counted correctly."""
        citations = [
            CitationInput(
                url="https://rozetka.com.ua/ua/mobile-phones/xyz", text=""
            ),
            CitationInput(
                url="https://rozetka.com.ua/ua/mobile-phones/abc", text=""
            ),
            CitationInput(url="https://rozetka.com.ua/ua/laptops/def", text=""),
        ]

        result = self.builder.aggregate(citations)

        # Domain level
        domain_item = next(
            i for i in result.items if i.path == "rozetka.com.ua" and i.is_domain
        )
        assert domain_item.count == 3

        # Sub-path: /ua should have 3
        ua_item = next(
            i for i in result.items if i.path == "rozetka.com.ua/ua"
        )
        assert ua_item.count == 3

        # Sub-path: /ua/mobile-phones should have 2
        mobile_item = next(
            i for i in result.items if i.path == "rozetka.com.ua/ua/mobile-phones"
        )
        assert mobile_item.count == 2

        # Sub-path: /ua/laptops should have 1
        laptops_item = next(
            i for i in result.items if i.path == "rozetka.com.ua/ua/laptops"
        )
        assert laptops_item.count == 1

    def test_aggregate_multiple_domains(self):
        """Test aggregating citations from multiple domains."""
        citations = [
            CitationInput(url="https://rozetka.com.ua/phones/123", text=""),
            CitationInput(url="https://moyo.ua/products/phone1", text=""),
            CitationInput(url="https://rozetka.com.ua/phones/456", text=""),
        ]

        result = self.builder.aggregate(citations)

        assert result.total_citations == 3

        domain_items = [i for i in result.items if i.is_domain]
        domain_paths = {i.path: i.count for i in domain_items}

        assert domain_paths["rozetka.com.ua"] == 2
        assert domain_paths["moyo.ua"] == 1

    def test_aggregate_sorted_by_count(self):
        """Test that results are sorted by count descending."""
        citations = [
            CitationInput(url="https://a.com/page1", text=""),
            CitationInput(url="https://b.com/page1", text=""),
            CitationInput(url="https://b.com/page2", text=""),
            CitationInput(url="https://c.com/page1", text=""),
            CitationInput(url="https://c.com/page2", text=""),
            CitationInput(url="https://c.com/page3", text=""),
        ]

        result = self.builder.aggregate(citations)

        # Domain items should be sorted by count desc
        domain_items = [i for i in result.items if i.is_domain]
        counts = [i.count for i in domain_items]
        assert counts == sorted(counts, reverse=True)

    def test_aggregate_empty_citations(self):
        """Test with empty citations list."""
        result = self.builder.aggregate([])

        assert result.total_citations == 0
        assert result.items == []

    def test_aggregate_malformed_url(self):
        """Test handling of malformed URLs."""
        citations = [
            CitationInput(url="not-a-valid-url", text=""),
            CitationInput(url="https://valid.com/page", text=""),
        ]

        result = self.builder.aggregate(citations)

        assert result.total_citations == 1
        assert len([i for i in result.items if i.is_domain]) == 1

    def test_aggregate_url_without_scheme(self):
        """Test URL without scheme (should be handled gracefully)."""
        citations = [
            CitationInput(url="rozetka.com.ua/phones", text=""),
        ]

        result = self.builder.aggregate(citations)

        # URL without scheme will have empty netloc, should be skipped
        assert result.total_citations == 0

    def test_aggregate_max_path_depth(self):
        """Test that max_path_depth limits path extraction."""
        builder = CitationLeaderboardBuilder(max_path_depth=1)
        citations = [
            CitationInput(
                url="https://example.com/a/b/c/d/e", text=""
            ),
        ]

        result = builder.aggregate(citations)

        paths = [item.path for item in result.items]
        assert "example.com" in paths
        assert "example.com/a" in paths
        assert "example.com/a/b" not in paths

    def test_aggregate_case_insensitive_domain(self):
        """Test that domain is case-insensitive."""
        citations = [
            CitationInput(url="https://ROZETKA.COM.UA/page1", text=""),
            CitationInput(url="https://rozetka.com.ua/page2", text=""),
        ]

        result = self.builder.aggregate(citations)

        domain_items = [i for i in result.items if i.is_domain]
        assert len(domain_items) == 1
        assert domain_items[0].path == "rozetka.com.ua"
        assert domain_items[0].count == 2

    def test_aggregate_url_with_query_params(self):
        """Test that query params are not included in path."""
        citations = [
            CitationInput(
                url="https://example.com/page?foo=bar&baz=qux", text=""
            ),
        ]

        result = self.builder.aggregate(citations)

        paths = [item.path for item in result.items]
        assert "example.com" in paths
        assert "example.com/page" in paths
        # Query params should not be part of path
        assert not any("?" in p for p in paths)

    def test_aggregate_url_with_trailing_slash(self):
        """Test URLs with trailing slashes."""
        citations = [
            CitationInput(url="https://example.com/page/", text=""),
        ]

        result = self.builder.aggregate(citations)

        paths = [item.path for item in result.items]
        assert "example.com" in paths
        assert "example.com/page" in paths

    def test_is_domain_flag(self):
        """Test that is_domain flag is set correctly."""
        citations = [
            CitationInput(url="https://example.com/path/subpath", text=""),
        ]

        result = self.builder.aggregate(citations)

        domain_items = [i for i in result.items if i.is_domain]
        path_items = [i for i in result.items if not i.is_domain]

        assert len(domain_items) == 1
        assert domain_items[0].path == "example.com"

        assert len(path_items) == 2
        path_paths = [i.path for i in path_items]
        assert "example.com/path" in path_paths
        assert "example.com/path/subpath" in path_paths
