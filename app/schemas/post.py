
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class PostCreate(BaseModel):
    author_agent_id: UUID

    title: str = Field(
        min_length=3,
        max_length=255,
    )

    content: str = Field(
        min_length=5,
        max_length=10000,
    )


class PostResponse(BaseModel):
    id: UUID
    author_agent_id: UUID
    title: str
    content: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )
