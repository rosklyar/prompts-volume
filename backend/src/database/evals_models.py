"""SQLAlchemy ORM models for evals_db tables."""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.evals_session import EvalsBase


class EvaluationStatus(str, enum.Enum):
    """Evaluation status enum."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportItemStatus(str, enum.Enum):
    """Status of a report item."""
    INCLUDED = "included"
    AWAITING = "awaiting"
    SKIPPED = "skipped"


class AIAssistant(EvalsBase):
    """AI Assistant model for tracking supported assistants."""

    __tablename__ = "ai_assistants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    def __repr__(self) -> str:
        return f"<AIAssistant(id={self.id}, name='{self.name}')>"


class PromptEvaluation(EvalsBase):
    """Track evaluations of prompts by different AI assistants.

    Note: Multiple evaluations can exist for the same (prompt_id, assistant_id)
    combination to support retry scenarios when evaluations timeout or fail.
    """

    __tablename__ = "prompt_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    prompt_id: Mapped[int] = mapped_column(
        Integer,  # No ForeignKey - prompts table is in prompts_db
        nullable=False,
        index=True
    )

    # AI Assistant identifier
    assistant_id: Mapped[int] = mapped_column(
        ForeignKey("ai_assistants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Status tracking
    status: Mapped[EvaluationStatus] = mapped_column(
        Enum(
            EvaluationStatus,
            values_callable=lambda x: [e.value for e in x],
            name="evaluationstatus",
        ),
        nullable=False,
        default=EvaluationStatus.IN_PROGRESS,
        index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        index=True
    )
    claimed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )

    # Result (JSON with response, citations, timestamp)
    answer: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships (within evals_db only)
    assistant: Mapped["AIAssistant"] = relationship()

    def __repr__(self) -> str:
        return f"<PromptEvaluation(id={self.id}, prompt_id={self.prompt_id}, assistant_id={self.assistant_id}, status='{self.status.value}')>"


class ConsumedEvaluation(EvalsBase):
    """Tracks which evaluations a user has paid for."""

    __tablename__ = "consumed_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )  # No FK - user is in users_db
    evaluation_id: Mapped[int] = mapped_column(
        ForeignKey("prompt_evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount_charged: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )
    consumed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships (within evals_db only)
    evaluation: Mapped["PromptEvaluation"] = relationship()

    # Constraints - each evaluation can only be consumed once per user
    __table_args__ = (
        UniqueConstraint("user_id", "evaluation_id", name="uq_consumed_eval_user_eval"),
    )

    def __repr__(self) -> str:
        return f"<ConsumedEvaluation(id={self.id}, user_id='{self.user_id}', evaluation_id={self.evaluation_id})>"


# =============================================================================
# Report Models
# =============================================================================


class GroupReport(EvalsBase):
    """Report snapshot for a prompt group."""

    __tablename__ = "group_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        Integer,  # No ForeignKey - prompt_groups table is in prompts_db
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )  # No FK - user is in users_db

    # Report metadata
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        index=True,
    )

    # Stats snapshot
    total_prompts: Mapped[int] = mapped_column(Integer, nullable=False)
    prompts_with_data: Mapped[int] = mapped_column(Integer, nullable=False)
    prompts_awaiting: Mapped[int] = mapped_column(Integer, nullable=False)
    total_evaluations_loaded: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)

    # Brand/competitors snapshot at report generation time
    brand_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    competitors_snapshot: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Relationships (within evals_db only)
    items: Mapped[List["GroupReportItem"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<GroupReport(id={self.id}, group_id={self.group_id}, created_at='{self.created_at}')>"


class GroupReportItem(EvalsBase):
    """Individual prompt/evaluation reference in a report."""

    __tablename__ = "group_report_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("group_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt_id: Mapped[int] = mapped_column(
        Integer,  # No ForeignKey - prompts table is in prompts_db
        nullable=False,
        index=True,
    )
    evaluation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("prompt_evaluations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Status at time of report
    status: Mapped[ReportItemStatus] = mapped_column(
        Enum(
            ReportItemStatus,
            values_callable=lambda x: [e.value for e in x],
            name="reportitemstatus",
        ),
        nullable=False,
    )
    is_fresh: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Amount charged (for this specific item in this report)
    amount_charged: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 4),
        nullable=True,
    )

    # Relationships (within evals_db only)
    report: Mapped["GroupReport"] = relationship(back_populates="items")
    evaluation: Mapped[Optional["PromptEvaluation"]] = relationship()

    def __repr__(self) -> str:
        return f"<GroupReportItem(id={self.id}, report_id={self.report_id}, prompt_id={self.prompt_id}, status='{self.status.value}')>"


# =============================================================================
# Bright Data Batch Models
# =============================================================================


class BrightDataBatchStatus(str, enum.Enum):
    """Status of a Bright Data batch."""
    PENDING = "pending"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class BrightDataBatch(EvalsBase):
    """Tracks Bright Data scraping batches for webhook correlation.

    When user requests fresh execution with BRIGHTDATA_ANSWERS=true,
    a batch is registered here. When the webhook arrives, we look up
    the batch to find which prompt_ids were requested.
    """

    __tablename__ = "brightdata_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    prompt_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer),
        nullable=False,
    )
    assistant_id: Mapped[int] = mapped_column(
        ForeignKey("ai_assistants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        server_default="1",  # Default to ChatGPT
    )
    status: Mapped[BrightDataBatchStatus] = mapped_column(
        Enum(
            BrightDataBatchStatus,
            values_callable=lambda x: [e.value for e in x],
            name="brightdatabatchstatus",
        ),
        nullable=False,
        default=BrightDataBatchStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<BrightDataBatch(id={self.id}, batch_id='{self.batch_id}', status='{self.status.value}')>"


# =============================================================================
# Daily Schedule Batch Models
# =============================================================================


class DailyBatchStatus(str, enum.Enum):
    """Status of a daily schedule batch."""
    COLLECTING = "collecting"    # Determining prompts to refresh
    REQUESTING = "requesting"    # Sending to BrightData
    AWAITING = "awaiting"        # Waiting for webhooks
    GENERATING = "generating"    # Generating reports
    COMPLETED = "completed"
    FAILED = "failed"


class DailyBatchGroupStatus(str, enum.Enum):
    """Status of a group within a daily batch."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class DailyScheduleBatch(EvalsBase):
    """Tracks a single daily batch processing run.

    Lifecycle:
    1. Created at 6 AM UTC when daily job starts
    2. Collects all groups with schedule_enabled=true
    3. Aggregates prompts needing refresh
    4. Triggers BrightData batches
    5. Waits for webhooks or timeout (6 hours)
    6. Generates reports for all groups
    """

    __tablename__ = "daily_schedule_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    scheduled_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[DailyBatchStatus] = mapped_column(
        Enum(
            DailyBatchStatus,
            values_callable=lambda x: [e.value for e in x],
            name="dailybatchstatus",
        ),
        nullable=False,
        default=DailyBatchStatus.COLLECTING,
    )

    # BrightData batch IDs for webhook correlation
    batch_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String(36)),
        nullable=False,
        default=[],
    )

    # Groups included in this batch
    group_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer),
        nullable=False,
        default=[],
    )

    # Prompt stats
    total_prompts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompts_needing_refresh: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompts_already_fresh: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    timeout_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    group_results: Mapped[List["DailyBatchGroupResult"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DailyScheduleBatch(id={self.id}, date='{self.scheduled_date}', status='{self.status.value}')>"


class DailyBatchGroupResult(EvalsBase):
    """Per-group result within a daily batch.

    Tracks the state of each group's report generation within a daily batch.
    Stores the evaluation selections made at scheduling time.
    """

    __tablename__ = "daily_batch_group_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("daily_schedule_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group_id: Mapped[int] = mapped_column(
        Integer,  # No ForeignKey - prompt_groups is in prompts_db
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )  # No FK - user is in users_db

    # Status
    status: Mapped[DailyBatchGroupStatus] = mapped_column(
        Enum(
            DailyBatchGroupStatus,
            values_callable=lambda x: [e.value for e in x],
            name="dailybatchgroupstatus",
        ),
        nullable=False,
        default=DailyBatchGroupStatus.PENDING,
    )

    # Generated report reference
    report_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("group_reports.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Prompt stats for this group
    prompts_in_group: Mapped[int] = mapped_column(Integer, nullable=False)
    prompts_needing_refresh: Mapped[int] = mapped_column(Integer, nullable=False)
    prompts_already_fresh: Mapped[int] = mapped_column(Integer, nullable=False)

    # Pre-recorded evaluation selections (prompt_id -> evaluation_id for fresh prompts)
    fresh_prompt_selections: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Map of prompt_id -> evaluation_id for prompts that were fresh at scheduling time"
    )

    # Relationships
    batch: Mapped["DailyScheduleBatch"] = relationship(back_populates="group_results")
    report: Mapped[Optional["GroupReport"]] = relationship()

    def __repr__(self) -> str:
        return f"<DailyBatchGroupResult(id={self.id}, batch_id={self.batch_id}, group_id={self.group_id}, status='{self.status.value}')>"
