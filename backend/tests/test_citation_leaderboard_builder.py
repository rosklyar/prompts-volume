"""Unit tests for CitationLeaderboardBuilder service."""

import pytest

from src.reports.services.citation_leaderboard_builder import (
    CitationInput,
    CitationLeaderboardBuilder,
)


class TestCitationLeaderboardBuilder:
    """Tests for CitationLeaderboardBuilder."""

    def setup_method(self):
        """Set up test fixtures."""
        self.builder = CitationLeaderboardBuilder(max_path_depth=2)

    def test_aggregate_multiple_domains(self):
        """Test aggregating citations from multiple domains."""
        citations = [
            CitationInput(url="https://rozetka.com.ua/phones/123", text=""),
            CitationInput(url="https://moyo.ua/products/phone1", text=""),
            CitationInput(url="https://rozetka.com.ua/phones/456", text=""),
        ]

        result = self.builder.aggregate(citations)

        assert result.total_citations == 3

        domain_paths = {i.path: i.count for i in result.domains}

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
        counts = [i.count for i in result.domains]
        assert counts == sorted(counts, reverse=True)

    def test_aggregate_multiple_path_levels(self):
        """Test aggregation at multiple path levels."""
        citations = [
            CitationInput(
                url="https://rozetka.com.ua/ua/mobile-phones/xyz", text=""
            ),
        ]

        result = self.builder.aggregate(citations)

        domain_paths = [item.path for item in result.domains]
        subpath_paths = [item.path for item in result.subpaths]
        assert "rozetka.com.ua" in domain_paths
        assert "rozetka.com.ua/ua" in subpath_paths
        assert "rozetka.com.ua/ua/mobile-phones" in subpath_paths
