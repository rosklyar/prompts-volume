"""Factory to build a predicate chain from JSON config."""

from src.keyword_inspiration.predicates.base import KeywordPredicate, KeywordPredicateChain
from src.keyword_inspiration.predicates.word_count import WordCountPredicate

_REGISTRY: dict[str, type] = {
    "word_count": WordCountPredicate,
}


def build_chain_from_config(config: list[dict] | None) -> KeywordPredicateChain:
    if not config:
        return KeywordPredicateChain([])
    predicates: list[KeywordPredicate] = []
    for entry in config:
        predicate_type = entry["type"]
        cls = _REGISTRY.get(predicate_type)
        if cls is None:
            raise ValueError(f"Unknown predicate type: {predicate_type}")
        params = {k: v for k, v in entry.items() if k != "type"}
        predicates.append(cls(**params))
    return KeywordPredicateChain(predicates)
