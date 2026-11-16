
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FeedbackCreate(BaseModel):
    post_id: UUID
    agent_id: UUID
    rating: int = Field(ge=1, le=5)
    feedback_type: Literal[
        "RELEVANT",
        "IRRELEVANT",
        "USEFUL",
        "NOT_USEFUL",
    ]
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    id: UUID
    post_id: UUID
    agent_id: UUID
    rating: int
    feedback_type: str
    comment: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
