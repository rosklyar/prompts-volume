"""Unit tests for CitationLeaderboardBuilder service."""

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
        # Simulate 3 answers, each with one citation
        citations_by_answer = [
            [CitationInput(url="https://rozetka.com.ua/phones/123", text="")],
            [CitationInput(url="https://moyo.ua/products/phone1", text="")],
            [CitationInput(url="https://rozetka.com.ua/phones/456", text="")],
        ]

        result = self.builder.aggregate(citations_by_answer)

        assert result.total_citations == 3
        assert result.total_answers == 3

        domain_paths = {i.path: i.count for i in result.domains}

        assert domain_paths["rozetka.com.ua"] == 2
        assert domain_paths["moyo.ua"] == 1

        # Check coverage for domains
        domain_coverage = {i.path: i.coverage_percent for i in result.domains}
        # rozetka appears in 2 out of 3 answers = 66.7%
        assert domain_coverage["rozetka.com.ua"] == 66.7
        # moyo appears in 1 out of 3 answers = 33.3%
        assert domain_coverage["moyo.ua"] == 33.3

    def test_aggregate_sorted_by_count(self):
        """Test that results are sorted by count descending."""
        # Simulate 6 answers, each with one citation
        citations_by_answer = [
            [CitationInput(url="https://a.com/page1", text="")],
            [CitationInput(url="https://b.com/page1", text="")],
            [CitationInput(url="https://b.com/page2", text="")],
            [CitationInput(url="https://c.com/page1", text="")],
            [CitationInput(url="https://c.com/page2", text="")],
            [CitationInput(url="https://c.com/page3", text="")],
        ]

        result = self.builder.aggregate(citations_by_answer)

        # Domain items should be sorted by count desc
        counts = [i.count for i in result.domains]
        assert counts == sorted(counts, reverse=True)

    def test_aggregate_multiple_path_levels(self):
        """Test aggregation at multiple path levels."""
        citations_by_answer = [
            [
                CitationInput(
                    url="https://rozetka.com.ua/ua/mobile-phones/xyz", text=""
                )
            ],
        ]

        result = self.builder.aggregate(citations_by_answer)

        domain_paths = [item.path for item in result.domains]
        subpath_paths = [item.path for item in result.subpaths]
        assert "rozetka.com.ua" in domain_paths
        assert "rozetka.com.ua/ua" in subpath_paths
        assert "rozetka.com.ua/ua/mobile-phones" in subpath_paths

    def test_aggregate_coverage_same_domain_in_one_answer(self):
        """Test that multiple citations to same domain in one answer count as 1 for coverage."""
        # Simulate 2 answers: first answer has 2 citations to same domain
        citations_by_answer = [
            [
                CitationInput(url="https://rozetka.com.ua/phones/123", text=""),
                CitationInput(url="https://rozetka.com.ua/phones/456", text=""),
            ],
            [CitationInput(url="https://moyo.ua/products/phone1", text="")],
        ]

        result = self.builder.aggregate(citations_by_answer)

        assert result.total_citations == 3
        assert result.total_answers == 2

        domain_coverage = {i.path: i.coverage_percent for i in result.domains}
        domain_counts = {i.path: i.count for i in result.domains}

        # rozetka has 2 citations but only appears in 1 answer = 50% coverage
        assert domain_counts["rozetka.com.ua"] == 2
        assert domain_coverage["rozetka.com.ua"] == 50.0

        # moyo has 1 citation and appears in 1 answer = 50% coverage
        assert domain_counts["moyo.ua"] == 1
        assert domain_coverage["moyo.ua"] == 50.0

    def test_aggregate_empty_answers(self):
        """Test aggregation with some empty answer lists."""
        citations_by_answer = [
            [CitationInput(url="https://rozetka.com.ua/phones/123", text="")],
            [],  # Empty answer
            [CitationInput(url="https://rozetka.com.ua/phones/456", text="")],
        ]

        result = self.builder.aggregate(citations_by_answer)

        assert result.total_citations == 2
        assert result.total_answers == 3

        domain_coverage = {i.path: i.coverage_percent for i in result.domains}
        # rozetka appears in 2 out of 3 answers = 66.7%
        assert domain_coverage["rozetka.com.ua"] == 66.7
