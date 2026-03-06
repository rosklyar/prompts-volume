"""Word count predicate for keyword filtering."""

from typing import Literal

from src.keyword_inspiration.models.domain import RankedKeyword

Operator = Literal["gt", "gte", "lt", "lte", "eq"]


class WordCountPredicate:
    def __init__(self, *, operator: Operator, value: int):
        self._operator = operator
        self._value = value

    def test(self, keyword: RankedKeyword) -> bool:
        count = len(keyword.keyword.split())
        match self._operator:
            case "gt":
                return count > self._value
            case "gte":
                return count >= self._value
            case "lt":
                return count < self._value
            case "lte":
                return count <= self._value
            case "eq":
                return count == self._value
