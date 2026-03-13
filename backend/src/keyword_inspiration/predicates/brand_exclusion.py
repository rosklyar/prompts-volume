"""Brand exclusion predicate for keyword filtering."""

from src.keyword_inspiration.models.domain import RankedKeyword


class BrandExclusionPredicate:
    def __init__(self, *, brand_names: list[str]):
        self._brand_names = [name.lower() for name in brand_names]

    def test(self, keyword: RankedKeyword) -> bool:
        kw_lower = keyword.keyword.lower()
        return not any(brand in kw_lower for brand in self._brand_names)
