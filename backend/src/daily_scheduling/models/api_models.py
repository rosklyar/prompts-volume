"""API models for daily scheduling endpoints."""

from datetime import datetime

from pydantic import BaseModel


class ScheduleConfigRequest(BaseModel):
    """Request to enable/disable schedule for a group."""

    enabled: bool


class ScheduleConfigResponse(BaseModel):
    """Response with current schedule configuration."""

    group_id: int
    enabled: bool
    last_run_at: datetime | None
