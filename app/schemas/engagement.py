
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EngagementCreate(BaseModel):
    post_id: UUID
    agent_id: UUID
    decision: Literal["ENGAGE", "SKIP"]
    reason: str | None = Field(default=None, max_length=1000)


class EngagementResponse(BaseModel):
    id: UUID
    post_id: UUID
    agent_id: UUID
    decision: str
    reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
