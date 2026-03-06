"""Base protocol and chain for keyword predicates."""

from typing import Protocol

from src.keyword_inspiration.models.domain import RankedKeyword


class KeywordPredicate(Protocol):
    def test(self, keyword: RankedKeyword) -> bool: ...


class KeywordPredicateChain:
    def __init__(self, predicates: list[KeywordPredicate]):
        self._predicates = predicates

    def apply(self, keywords: list[RankedKeyword]) -> list[RankedKeyword]:
        if not self._predicates:
            return keywords
        return [kw for kw in keywords if all(p.test(kw) for p in self._predicates)]
