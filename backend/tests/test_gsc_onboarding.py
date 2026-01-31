"""Tests for GSC onboarding services."""

import pytest

from src.gsc.models import GSCSiteInfo, SearchQueryRow
from src.gsc.services.property_matcher import PropertyMatcher, PropertyMatch
from src.gsc.services.keyword_filter import MinWordCountFilter, CompositeFilter


class TestPropertyMatcher:
    """Tests for PropertyMatcher."""

    def test_exact_match_domain_property(self):
        """Test exact match with sc-domain format."""
        matcher = PropertyMatcher()
        properties = [
            GSCSiteInfo(site_url="sc-domain:example.com", permission_level="siteOwner"),
        ]

        result = matcher.match("example.com", properties)

        assert result.match_type == "exact"
        assert result.matched_property == "sc-domain:example.com"

    def test_exact_match_url_prefix(self):
        """Test exact match with URL prefix format."""
        matcher = PropertyMatcher()
        properties = [
            GSCSiteInfo(site_url="https://example.com/", permission_level="siteOwner"),
        ]

        result = matcher.match("example.com", properties)

        assert result.match_type == "exact"
        assert result.matched_property == "https://example.com/"

    def test_exact_match_with_www_prefix(self):
        """Test matching ignores www prefix."""
        matcher = PropertyMatcher()
        properties = [
            GSCSiteInfo(site_url="sc-domain:example.com", permission_level="siteOwner"),
        ]

        result = matcher.match("www.example.com", properties)

        assert result.match_type == "exact"
        assert result.matched_property == "sc-domain:example.com"

    def test_exact_match_case_insensitive(self):
        """Test matching is case insensitive."""
        matcher = PropertyMatcher()
        properties = [
            GSCSiteInfo(site_url="sc-domain:Example.COM", permission_level="siteOwner"),
        ]

        result = matcher.match("EXAMPLE.com", properties)

        assert result.match_type == "exact"
        assert result.matched_property == "sc-domain:Example.COM"

    def test_partial_match_subdomain(self):
        """Test partial match with subdomain."""
        matcher = PropertyMatcher()
        properties = [
            GSCSiteInfo(site_url="sc-domain:blog.example.com", permission_level="siteOwner"),
        ]

        result = matcher.match("example.com", properties)

        assert result.match_type == "partial"
        assert result.matched_property == "sc-domain:blog.example.com"

    def test_multiple_matches(self):
        """Test multiple matches returns 'multiple' type."""
        matcher = PropertyMatcher()
        properties = [
            GSCSiteInfo(site_url="sc-domain:example.com", permission_level="siteOwner"),
            GSCSiteInfo(site_url="https://example.com/", permission_level="siteFullUser"),
        ]

        result = matcher.match("example.com", properties)

        assert result.match_type == "multiple"
        assert result.matched_property is None
        assert len(result.available_properties) == 2

    def test_no_match(self):
        """Test no match returns 'none' type."""
        matcher = PropertyMatcher()
        properties = [
            GSCSiteInfo(site_url="sc-domain:other.com", permission_level="siteOwner"),
        ]

        result = matcher.match("example.com", properties)

        assert result.match_type == "none"
        assert result.matched_property is None
        assert len(result.available_properties) == 1

    def test_empty_properties(self):
        """Test empty properties list."""
        matcher = PropertyMatcher()

        result = matcher.match("example.com", [])

        assert result.match_type == "none"
        assert result.matched_property is None
        assert len(result.available_properties) == 0

    def test_brand_domain_with_protocol(self):
        """Test brand domain with protocol is normalized."""
        matcher = PropertyMatcher()
        properties = [
            GSCSiteInfo(site_url="sc-domain:example.com", permission_level="siteOwner"),
        ]

        result = matcher.match("https://example.com", properties)

        assert result.match_type == "exact"


class TestMinWordCountFilter:
    """Tests for MinWordCountFilter."""

    def test_filter_keeps_long_queries(self):
        """Test filter keeps queries with enough words."""
        filter_ = MinWordCountFilter(min_words=3)
        rows = [
            SearchQueryRow(keys=["best running shoes for flat feet"], clicks=100, impressions=1000, ctr=0.1, position=5.0),
            SearchQueryRow(keys=["running shoes"], clicks=200, impressions=2000, ctr=0.1, position=3.0),
        ]

        result = filter_.filter(rows)

        assert len(result) == 1
        assert result[0].keys[0] == "best running shoes for flat feet"

    def test_filter_default_min_words(self):
        """Test default min_words is 3."""
        filter_ = MinWordCountFilter()
        rows = [
            SearchQueryRow(keys=["one two"], clicks=10, impressions=100, ctr=0.1, position=1.0),
            SearchQueryRow(keys=["one two three"], clicks=10, impressions=100, ctr=0.1, position=1.0),
        ]

        result = filter_.filter(rows)

        assert len(result) == 1
        assert result[0].keys[0] == "one two three"

    def test_filter_empty_keys_skipped(self):
        """Test rows with empty keys are skipped."""
        filter_ = MinWordCountFilter(min_words=1)
        rows = [
            SearchQueryRow(keys=[], clicks=10, impressions=100, ctr=0.1, position=1.0),
            SearchQueryRow(keys=["valid query"], clicks=10, impressions=100, ctr=0.1, position=1.0),
        ]

        result = filter_.filter(rows)

        assert len(result) == 1
        assert result[0].keys[0] == "valid query"

    def test_filter_invalid_min_words_raises(self):
        """Test min_words < 1 raises ValueError."""
        with pytest.raises(ValueError, match="min_words must be at least 1"):
            MinWordCountFilter(min_words=0)

    def test_filter_custom_min_words(self):
        """Test custom min_words value."""
        filter_ = MinWordCountFilter(min_words=5)
        rows = [
            SearchQueryRow(keys=["one two three four"], clicks=10, impressions=100, ctr=0.1, position=1.0),
            SearchQueryRow(keys=["one two three four five"], clicks=10, impressions=100, ctr=0.1, position=1.0),
        ]

        result = filter_.filter(rows)

        assert len(result) == 1
        assert result[0].keys[0] == "one two three four five"


class TestCompositeFilter:
    """Tests for CompositeFilter."""

    def test_composite_applies_all_filters(self):
        """Test composite filter applies all filters in sequence."""
        filter1 = MinWordCountFilter(min_words=2)
        filter2 = MinWordCountFilter(min_words=3)
        composite = CompositeFilter([filter1, filter2])

        rows = [
            SearchQueryRow(keys=["one"], clicks=10, impressions=100, ctr=0.1, position=1.0),
            SearchQueryRow(keys=["one two"], clicks=10, impressions=100, ctr=0.1, position=1.0),
            SearchQueryRow(keys=["one two three"], clicks=10, impressions=100, ctr=0.1, position=1.0),
        ]

        result = composite.filter(rows)

        assert len(result) == 1
        assert result[0].keys[0] == "one two three"

    def test_composite_empty_filters(self):
        """Test composite with no filters returns original list."""
        composite = CompositeFilter([])
        rows = [
            SearchQueryRow(keys=["test"], clicks=10, impressions=100, ctr=0.1, position=1.0),
        ]

        result = composite.filter(rows)

        assert len(result) == 1
