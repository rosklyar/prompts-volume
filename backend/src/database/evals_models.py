"""SQLAlchemy ORM models for evals_db tables."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.evals_session import EvalsBase


class EvaluationStatus(str, enum.Enum):
    """Evaluation status enum."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionQueueStatus(str, enum.Enum):
    """Status of an execution queue item."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


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

    # Relationships
    plans: Mapped[List["AIAssistantPlan"]] = relationship(
        back_populates="assistant",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AIAssistant(id={self.id}, name='{self.name}')>"


class AIAssistantPlan(EvalsBase):
    """AI Assistant Plan model for tracking supported plans per assistant."""

    __tablename__ = "ai_assistant_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    assistant_id: Mapped[int] = mapped_column(
        ForeignKey("ai_assistants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationships
    assistant: Mapped["AIAssistant"] = relationship(back_populates="plans")
    evaluations: Mapped[List["PromptEvaluation"]] = relationship(
        back_populates="assistant_plan",
        cascade="all, delete-orphan"
    )

    # Constraints - ensure unique plan names per assistant
    __table_args__ = (
        UniqueConstraint("assistant_id", "name", name="uq_assistant_plan"),
    )

    def __repr__(self) -> str:
        return f"<AIAssistantPlan(id={self.id}, assistant_id={self.assistant_id}, name='{self.name}')>"


class ExecutionQueue(EvalsBase):
    """Unified queue for prompts awaiting execution.

    Replaces PriorityPromptQueue with demand-driven execution model.
    Prompts are only added when:
    1. Newly added by admin/user
    2. User explicitly requests fresh execution when generating a report
    """

    __tablename__ = "execution_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    prompt_id: Mapped[int] = mapped_column(
        Integer,  # No ForeignKey - prompts table is in prompts_db
        nullable=False,
        index=True,
    )
    requested_by: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )  # User ID or 'system' for admin-added prompts
    request_batch_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )  # Groups prompts from same "Request Fresh" action
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        index=True,  # For FIFO ordering
    )
    status: Mapped[ExecutionQueueStatus] = mapped_column(
        Enum(
            ExecutionQueueStatus,
            values_callable=lambda x: [e.value for e in x],
            name="executionqueuestatus",
        ),
        nullable=False,
        default=ExecutionQueueStatus.PENDING,
        index=True,
    )
    claimed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    evaluation_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("prompt_evaluations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )  # Reference to resulting evaluation

    # Relationships
    evaluation: Mapped[Optional["PromptEvaluation"]] = relationship()

    # GLOBAL unique constraint: prompt can only be in queue once (regardless of user)
    # when status is pending or in_progress
    __table_args__ = (
        Index(
            "uq_execution_queue_prompt_active",
            "prompt_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'in_progress')"),
        ),
    )

    def __repr__(self) -> str:
        return f"<ExecutionQueue(id={self.id}, prompt_id={self.prompt_id}, status='{self.status.value}')>"


class PromptEvaluation(EvalsBase):
    """Track evaluations of prompts by different AI assistants.

    Note: Multiple evaluations can exist for the same (prompt_id, assistant_plan_id)
    combination to support retry scenarios when evaluations timeout or fail.
    """

    __tablename__ = "prompt_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    prompt_id: Mapped[int] = mapped_column(
        Integer,  # No ForeignKey - prompts table is in prompts_db
        nullable=False,
        index=True
    )

    # Assistant plan identifier (references ai_assistant_plans in same db)
    assistant_plan_id: Mapped[int] = mapped_column(
        ForeignKey("ai_assistant_plans.id", ondelete="CASCADE"),
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
    assistant_plan: Mapped["AIAssistantPlan"] = relationship(back_populates="evaluations")

    def __repr__(self) -> str:
        return f"<PromptEvaluation(id={self.id}, prompt_id={self.prompt_id}, assistant_plan_id={self.assistant_plan_id}, status='{self.status.value}')>"


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
