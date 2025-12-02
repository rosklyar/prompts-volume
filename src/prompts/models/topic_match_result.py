"""Result model for topic matching operation."""

from dataclasses import dataclass
from typing import List

from src.database import Topic
from src.prompts.models.generated_topic import GeneratedTopic


@dataclass
class TopicMatchResult:
    """Result of matching generated topics with DB topics."""

    matched_topics: List[Topic]  # ORM Topic objects from DB
    unmatched_topics: List[GeneratedTopic]  # Generated topics without DB match

    def all_topic_titles(self) -> List[str]:
        """Get all topic titles (matched + unmatched) as strings."""
        return (
            [t.title for t in self.matched_topics] +
            [t.title for t in self.unmatched_topics]
        )
