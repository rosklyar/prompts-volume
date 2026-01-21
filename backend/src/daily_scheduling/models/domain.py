"""Domain models for daily scheduling."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class EnabledGroup:
    """Group with scheduling enabled."""

    group_id: int
    user_id: str
    title: str
    country_id: int
    country_iso_code: str


@dataclass(frozen=True)
class PromptFreshnessInfo:
    """Freshness information for a prompt."""

    prompt_id: int
    prompt_text: str
    needs_refresh: bool
    latest_evaluation_id: int | None


@dataclass(frozen=True)
class GroupPromptAnalysis:
    """Analysis of prompts in a group for scheduling."""

    group_id: int
    user_id: str
    prompts_needing_refresh: list[int]
    fresh_prompt_selections: dict[int, int]  # prompt_id -> evaluation_id


@dataclass(frozen=True)
class DailyBatchInfo:
    """Information about a daily batch."""

    batch_id: int
    scheduled_date: date
    status: str
    brightdata_batch_ids: list[str]
    group_ids: list[int]
    total_prompts: int
    prompts_needing_refresh: int
    prompts_already_fresh: int
    timeout_at: datetime
    is_timed_out: bool
    all_batches_complete: bool
