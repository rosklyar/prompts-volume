"""Composable keyword filtering predicates."""

from src.keyword_inspiration.predicates.base import KeywordPredicate, KeywordPredicateChain
from src.keyword_inspiration.predicates.registry import build_chain_from_config
from src.keyword_inspiration.predicates.word_count import WordCountPredicate

__all__ = [
    "KeywordPredicate",
    "KeywordPredicateChain",
    "WordCountPredicate",
    "build_chain_from_config",
]
