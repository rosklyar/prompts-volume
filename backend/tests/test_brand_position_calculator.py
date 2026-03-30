"""Unit tests for BrandPositionCalculator."""

import pytest

from src.reports.models.brand_models import BrandMentionResultModel, MentionPositionModel
from src.reports.models.export_models import BrandPositionScore, BrandVisibilityScore
from src.reports.services.statistics.brand_position import BrandPositionCalculator
from src.reports.services.statistics.brand_visibility import BrandConfig


def _mention(brand_name: str, starts: list[int]) -> BrandMentionResultModel:
    """Helper to build a BrandMentionResultModel with given start positions."""
    return BrandMentionResultModel(
        brand_name=brand_name,
        mentions=[
            MentionPositionModel(start=s, end=s + 5, matched_text="x", variation="x")
            for s in starts
        ],
    )


def _visibility(brand_name: str, *, is_target: bool, pct: float) -> BrandVisibilityScore:
    return BrandVisibilityScore(
        brand_name=brand_name,
        is_target_brand=is_target,
        prompts_with_mentions=0,
        total_prompts=0,
        visibility_percentage=pct,
    )


class TestBrandPositionCalculator:
    def setup_method(self):
        self.calc = BrandPositionCalculator()
        self.brands = [
            BrandConfig(name="Nike", is_target=True),
            BrandConfig(name="Adidas", is_target=False),
        ]

    def test_empty_input(self):
        result = self.calc.calculate(
            brand_mentions_per_item=[],
            brands=self.brands,
            visibility_scores=[],
        )
        assert len(result) == 2
        assert all(r.average_position == 0.0 for r in result)
        assert all(r.prompts_counted == 0 for r in result)
        assert all(r.reliability == "not_reliable" for r in result)

    def test_single_item_single_brand(self):
        mentions = [_mention("Nike", [10])]
        visibility = [_visibility("Nike", is_target=True, pct=100.0)]

        result = self.calc.calculate(
            brand_mentions_per_item=[mentions],
            brands=[BrandConfig(name="Nike", is_target=True)],
            visibility_scores=visibility,
        )

        assert len(result) == 1
        assert result[0].average_position == 1.0
        assert result[0].prompts_counted == 1
        assert result[0].reliability == "high_reliability"

    def test_two_brands_ranking(self):
        """Nike at position 10, Adidas at position 5 → Adidas=1, Nike=2."""
        mentions = [
            _mention("Nike", [10]),
            _mention("Adidas", [5]),
        ]
        visibility = [
            _visibility("Nike", is_target=True, pct=100.0),
            _visibility("Adidas", is_target=False, pct=100.0),
        ]

        result = self.calc.calculate(
            brand_mentions_per_item=[mentions],
            brands=self.brands,
            visibility_scores=visibility,
        )

        nike = next(r for r in result if r.brand_name == "Nike")
        adidas = next(r for r in result if r.brand_name == "Adidas")
        assert nike.average_position == 2.0
        assert adidas.average_position == 1.0

    def test_average_across_items(self):
        """Nike 1st in item1, 2nd in item2 → avg = 1.5."""
        item1 = [_mention("Nike", [5]), _mention("Adidas", [20])]
        item2 = [_mention("Nike", [30]), _mention("Adidas", [10])]
        visibility = [
            _visibility("Nike", is_target=True, pct=100.0),
            _visibility("Adidas", is_target=False, pct=100.0),
        ]

        result = self.calc.calculate(
            brand_mentions_per_item=[item1, item2],
            brands=self.brands,
            visibility_scores=visibility,
        )

        nike = next(r for r in result if r.brand_name == "Nike")
        adidas = next(r for r in result if r.brand_name == "Adidas")
        assert nike.average_position == 1.5
        assert adidas.average_position == 1.5

    def test_brand_not_mentioned_in_some_items(self):
        """Nike mentioned in 1/2 items, Adidas in both."""
        item1 = [_mention("Nike", [5]), _mention("Adidas", [20])]
        item2 = [_mention("Adidas", [10])]  # Nike not mentioned
        visibility = [
            _visibility("Nike", is_target=True, pct=50.0),
            _visibility("Adidas", is_target=False, pct=100.0),
        ]

        result = self.calc.calculate(
            brand_mentions_per_item=[item1, item2],
            brands=self.brands,
            visibility_scores=visibility,
        )

        nike = next(r for r in result if r.brand_name == "Nike")
        adidas = next(r for r in result if r.brand_name == "Adidas")
        assert nike.average_position == 1.0  # Only counted in item1 where it was 1st
        assert nike.prompts_counted == 1
        assert nike.total_prompts == 2
        assert adidas.prompts_counted == 2
        assert adidas.average_position == 1.5  # 2nd in item1, 1st in item2

    def test_none_items_skipped(self):
        """None entries (no answer) should be skipped."""
        mentions = [_mention("Nike", [10])]
        visibility = [_visibility("Nike", is_target=True, pct=50.0)]

        result = self.calc.calculate(
            brand_mentions_per_item=[None, mentions, None],
            brands=[BrandConfig(name="Nike", is_target=True)],
            visibility_scores=visibility,
        )

        assert result[0].total_prompts == 1  # Only 1 non-None item
        assert result[0].prompts_counted == 1

    def test_brand_zero_mentions(self):
        """Brand configured but never mentioned."""
        item = [_mention("Adidas", [10])]  # Only Adidas
        visibility = [
            _visibility("Nike", is_target=True, pct=0.0),
            _visibility("Adidas", is_target=False, pct=100.0),
        ]

        result = self.calc.calculate(
            brand_mentions_per_item=[item],
            brands=self.brands,
            visibility_scores=visibility,
        )

        nike = next(r for r in result if r.brand_name == "Nike")
        assert nike.average_position == 0.0
        assert nike.prompts_counted == 0
        assert nike.reliability == "not_reliable"

    @pytest.mark.parametrize(
        "pct,expected_reliability",
        [
            (0.0, "not_reliable"),
            (9.99, "not_reliable"),
            (10.0, "low_reliability"),
            (29.99, "low_reliability"),
            (30.0, "low_reliability"),
            (30.01, "reliable"),
            (60.0, "reliable"),
            (60.01, "high_reliability"),
            (100.0, "high_reliability"),
        ],
    )
    def test_reliability_tiers(self, pct: float, expected_reliability: str):
        assert BrandPositionCalculator._derive_reliability(pct) == expected_reliability
