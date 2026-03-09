"""Unit tests for keyword predicate chain."""

import pytest

from src.keyword_inspiration.models.domain import RankedKeyword
from src.keyword_inspiration.predicates.base import KeywordPredicateChain
from src.keyword_inspiration.predicates.registry import build_chain_from_config
from src.keyword_inspiration.predicates.brand_exclusion import BrandExclusionPredicate
from src.keyword_inspiration.predicates.word_count import WordCountPredicate


def _kw(text: str, volume: int = 100, rank: int = 1) -> RankedKeyword:
    return RankedKeyword(keyword=text, search_volume=volume, rank_group=rank)


SAMPLE_KEYWORDS = [
    _kw("tv"),                    # 1 word
    _kw("smart tv"),              # 2 words
    _kw("best smart tv 4k"),      # 4 words
    _kw("cheap laptop deals"),    # 3 words
]


class TestBrandExclusionPredicate:
    def test_excludes_keyword_containing_brand(self):
        p = BrandExclusionPredicate(brand_names=["moyo", "мойо"])
        assert p.test(_kw("smart tv")) is True
        assert p.test(_kw("moyo київ")) is False
        assert p.test(_kw("мойо доставка")) is False

    def test_case_insensitive(self):
        p = BrandExclusionPredicate(brand_names=["Dell"])
        assert p.test(_kw("laptop dell deals")) is False
        assert p.test(_kw("DELL monitor")) is False
        assert p.test(_kw("smart tv 4k")) is True

    def test_empty_brand_list_passes_all(self):
        p = BrandExclusionPredicate(brand_names=[])
        assert p.test(_kw("anything")) is True
        assert p.test(_kw("dell laptop")) is True


class TestWordCountPredicate:
    def test_gt(self):
        p = WordCountPredicate(operator="gt", value=2)
        assert p.test(_kw("one two three")) is True
        assert p.test(_kw("one two")) is False
        assert p.test(_kw("one")) is False

    def test_gte(self):
        p = WordCountPredicate(operator="gte", value=2)
        assert p.test(_kw("one two")) is True
        assert p.test(_kw("one")) is False

    def test_lt(self):
        p = WordCountPredicate(operator="lt", value=3)
        assert p.test(_kw("one two")) is True
        assert p.test(_kw("one two three")) is False

    def test_lte(self):
        p = WordCountPredicate(operator="lte", value=2)
        assert p.test(_kw("one two")) is True
        assert p.test(_kw("one two three")) is False

    def test_eq(self):
        p = WordCountPredicate(operator="eq", value=2)
        assert p.test(_kw("one two")) is True
        assert p.test(_kw("one")) is False
        assert p.test(_kw("one two three")) is False


class TestKeywordPredicateChain:
    def test_empty_chain_passes_all(self):
        chain = KeywordPredicateChain([])
        result = chain.apply(SAMPLE_KEYWORDS)
        assert result == SAMPLE_KEYWORDS

    def test_single_predicate(self):
        chain = KeywordPredicateChain([WordCountPredicate(operator="gte", value=3)])
        result = chain.apply(SAMPLE_KEYWORDS)
        assert [kw.keyword for kw in result] == ["best smart tv 4k", "cheap laptop deals"]

    def test_multiple_predicates(self):
        chain = KeywordPredicateChain([
            WordCountPredicate(operator="gte", value=2),
            WordCountPredicate(operator="lte", value=3),
        ])
        result = chain.apply(SAMPLE_KEYWORDS)
        assert [kw.keyword for kw in result] == ["smart tv", "cheap laptop deals"]


class TestBuildChainFromConfig:
    def test_none_config(self):
        chain = build_chain_from_config(None)
        result = chain.apply(SAMPLE_KEYWORDS)
        assert result == SAMPLE_KEYWORDS

    def test_empty_config(self):
        chain = build_chain_from_config([])
        result = chain.apply(SAMPLE_KEYWORDS)
        assert result == SAMPLE_KEYWORDS

    def test_valid_config(self):
        config = [{"type": "word_count", "operator": "gt", "value": 1}]
        chain = build_chain_from_config(config)
        result = chain.apply(SAMPLE_KEYWORDS)
        assert [kw.keyword for kw in result] == ["smart tv", "best smart tv 4k", "cheap laptop deals"]

    def test_unknown_type_raises(self):
        config = [{"type": "nonexistent", "value": 1}]
        with pytest.raises(ValueError, match="Unknown predicate type: nonexistent"):
            build_chain_from_config(config)

    def test_multiple_predicates_config(self):
        config = [
            {"type": "word_count", "operator": "gte", "value": 2},
            {"type": "word_count", "operator": "lt", "value": 4},
        ]
        chain = build_chain_from_config(config)
        result = chain.apply(SAMPLE_KEYWORDS)
        assert [kw.keyword for kw in result] == ["smart tv", "cheap laptop deals"]

    def test_brand_exclusion_with_brand_names(self):
        keywords = [_kw("smart tv"), _kw("moyo київ"), _kw("cheap laptop")]
        config = [{"type": "brand_exclusion"}]
        chain = build_chain_from_config(config, brand_names=["moyo"])
        result = chain.apply(keywords)
        assert [kw.keyword for kw in result] == ["smart tv", "cheap laptop"]

    def test_brand_exclusion_without_brand_names(self):
        keywords = [_kw("smart tv"), _kw("moyo київ")]
        config = [{"type": "brand_exclusion"}]
        chain = build_chain_from_config(config)
        result = chain.apply(keywords)
        assert [kw.keyword for kw in result] == ["smart tv", "moyo київ"]

    def test_combined_word_count_and_brand_exclusion(self):
        keywords = [_kw("tv"), _kw("smart tv"), _kw("moyo smart tv"), _kw("cheap laptop deals")]
        config = [
            {"type": "word_count", "operator": "gte", "value": 2},
            {"type": "brand_exclusion"},
        ]
        chain = build_chain_from_config(config, brand_names=["moyo"])
        result = chain.apply(keywords)
        assert [kw.keyword for kw in result] == ["smart tv", "cheap laptop deals"]
