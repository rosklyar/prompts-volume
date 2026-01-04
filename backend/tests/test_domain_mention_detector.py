"""Unit tests for DomainMentionDetector."""

import pytest

from src.reports.services.domain_mention_detector import (
    DomainInput,
    DomainMentionDetector,
)


@pytest.fixture
def detector():
    return DomainMentionDetector()


class TestBasicDomainMatch:
    """Tests for basic domain matching in text."""

    def test_bare_domain_match(self, detector):
        text = "Check out example.com for more info"
        domains = [DomainInput(name="Example", domain="example.com", is_brand=True)]
        results = detector.detect(text, domains)

        assert len(results) == 1
        assert results[0].name == "Example"
        assert results[0].is_brand is True
        assert len(results[0].mentions) == 1
        assert results[0].mentions[0].matched_text == "example.com"

    def test_domain_with_https(self, detector):
        text = "Visit https://example.com/page for details"
        domains = [DomainInput(name="Example", domain="example.com", is_brand=True)]
        results = detector.detect(text, domains)

        assert len(results) == 1
        assert len(results[0].mentions) == 1
        assert "https://example.com/page" in results[0].mentions[0].matched_text

    def test_domain_with_www(self, detector):
        text = "Go to www.example.com for help"
        domains = [DomainInput(name="Example", domain="example.com", is_brand=True)]
        results = detector.detect(text, domains)

        assert len(results) == 1
        assert len(results[0].mentions) == 1
        assert "www.example.com" in results[0].mentions[0].matched_text


class TestSubdomainMatch:
    """Tests for subdomain matching."""

    def test_subdomain_matches(self, detector):
        text = "Check blog.example.com for articles"
        domains = [DomainInput(name="Example", domain="example.com", is_brand=True)]
        results = detector.detect(text, domains)

        assert len(results) == 1
        assert len(results[0].mentions) == 1
        assert "blog.example.com" in results[0].mentions[0].matched_text

    def test_deep_subdomain_matches(self, detector):
        text = "API docs at api.v2.example.com/docs"
        domains = [DomainInput(name="Example", domain="example.com", is_brand=True)]
        results = detector.detect(text, domains)

        assert len(results) == 1
        assert len(results[0].mentions) == 1


class TestPathMatching:
    """Tests for URLs with paths."""

    def test_domain_with_path(self, detector):
        text = "See example.com/products/widget for the product"
        domains = [DomainInput(name="Example", domain="example.com", is_brand=True)]
        results = detector.detect(text, domains)

        assert len(results) == 1
        assert len(results[0].mentions) == 1
        assert "example.com/products/widget" in results[0].mentions[0].matched_text

    def test_full_url_with_path(self, detector):
        text = "Visit https://www.example.com/shop/items?id=123 now"
        domains = [DomainInput(name="Example", domain="example.com", is_brand=True)]
        results = detector.detect(text, domains)

        assert len(results) == 1
        assert len(results[0].mentions) == 1


class TestMultipleDomains:
    """Tests for multiple domains."""

    def test_brand_and_competitors(self, detector):
        text = "Compare shopify.com vs woocommerce.com for your store"
        domains = [
            DomainInput(name="Shopify", domain="shopify.com", is_brand=True),
            DomainInput(name="WooCommerce", domain="woocommerce.com", is_brand=False),
        ]
        results = detector.detect(text, domains)

        assert len(results) == 2

        shopify = next(r for r in results if r.name == "Shopify")
        assert shopify.is_brand is True
        assert len(shopify.mentions) == 1

        woo = next(r for r in results if r.name == "WooCommerce")
        assert woo.is_brand is False
        assert len(woo.mentions) == 1

    def test_domain_not_found(self, detector):
        text = "This text mentions nothing relevant"
        domains = [DomainInput(name="Example", domain="example.com", is_brand=True)]
        results = detector.detect(text, domains)

        assert len(results) == 1
        assert len(results[0].mentions) == 0


class TestMultipleMentions:
    """Tests for multiple mentions of same domain."""

    def test_multiple_mentions_same_domain(self, detector):
        text = "First example.com then https://example.com/page and blog.example.com"
        domains = [DomainInput(name="Example", domain="example.com", is_brand=True)]
        results = detector.detect(text, domains)

        assert len(results) == 1
        assert len(results[0].mentions) == 3


class TestPositionTracking:
    """Tests for position tracking."""

    def test_positions_are_correct(self, detector):
        text = "Visit example.com today"
        domains = [DomainInput(name="Example", domain="example.com", is_brand=True)]
        results = detector.detect(text, domains)

        mention = results[0].mentions[0]
        assert text[mention.start:mention.end] == mention.matched_text

    def test_positions_sorted(self, detector):
        text = "First example.com then later example.com/page"
        domains = [DomainInput(name="Example", domain="example.com", is_brand=True)]
        results = detector.detect(text, domains)

        mentions = results[0].mentions
        assert len(mentions) == 2
        assert mentions[0].start < mentions[1].start


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_text(self, detector):
        domains = [DomainInput(name="Example", domain="example.com", is_brand=True)]
        results = detector.detect("", domains)

        assert len(results) == 0

    def test_empty_domains(self, detector):
        results = detector.detect("Some text with example.com", [])

        assert len(results) == 0

    def test_domain_without_domain_value(self, detector):
        """Domain with None domain should be skipped."""
        text = "Check example.com"
        domains = [DomainInput(name="Example", domain="", is_brand=True)]
        results = detector.detect(text, domains)

        assert len(results) == 0

    def test_case_insensitive(self, detector):
        text = "Visit EXAMPLE.COM and Example.Com"
        domains = [DomainInput(name="Example", domain="example.com", is_brand=True)]
        results = detector.detect(text, domains)

        assert len(results) == 1
        assert len(results[0].mentions) == 2


class TestNoFalsePositives:
    """Tests to ensure no false positive matches."""

    def test_partial_domain_no_match(self, detector):
        """notexample.com should NOT match example.com"""
        text = "Check notexample.com for other stuff"
        domains = [DomainInput(name="Example", domain="example.com", is_brand=True)]
        results = detector.detect(text, domains)

        # Should not match notexample.com
        assert len(results) == 1
        assert len(results[0].mentions) == 0

    def test_similar_domain_no_match(self, detector):
        """example.org should NOT match example.com"""
        text = "Visit example.org instead"
        domains = [DomainInput(name="Example", domain="example.com", is_brand=True)]
        results = detector.detect(text, domains)

        assert len(results) == 1
        assert len(results[0].mentions) == 0
