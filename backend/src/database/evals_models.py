"""SQLAlchemy ORM models for evals_db tables."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, text
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


class PriorityPromptQueue(EvalsBase):
    """Queue for priority prompts that should be evaluated first."""

    __tablename__ = "priority_prompt_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    prompt_id: Mapped[int] = mapped_column(
        Integer,  # No ForeignKey - prompts table is in prompts_db
        nullable=False,
        unique=True,  # Each prompt can only be in queue once
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        index=True,  # For ordering by priority (FIFO within priority)
    )
    request_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,  # For querying all prompts from same request
    )

    def __repr__(self) -> str:
        return f"<PriorityPromptQueue(id={self.id}, prompt_id={self.prompt_id}, request_id='{self.request_id}')>"


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
