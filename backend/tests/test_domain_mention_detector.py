"""Unit tests for DomainMentionDetector."""

import pytest

from src.reports.services.domain_mention_detector import (
    DomainInput,
    DomainMentionDetector,
)


@pytest.fixture
def detector():
    return DomainMentionDetector()


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


class TestPositionTracking:
    """Tests for position tracking."""

    def test_positions_are_correct(self, detector):
        text = "Visit example.com today"
        domains = [DomainInput(name="Example", domain="example.com", is_brand=True)]
        results = detector.detect(text, domains)

        mention = results[0].mentions[0]
        assert text[mention.start:mention.end] == mention.matched_text


class TestSubdomainMatch:
    """Tests for subdomain matching."""

    def test_subdomain_matches(self, detector):
        text = "Check blog.example.com for articles"
        domains = [DomainInput(name="Example", domain="example.com", is_brand=True)]
        results = detector.detect(text, domains)

        assert len(results) == 1
        assert len(results[0].mentions) == 1
        assert "blog.example.com" in results[0].mentions[0].matched_text
