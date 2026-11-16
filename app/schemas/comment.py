
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CommentResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    content: str
    status: str
    created_at: datetime
    published_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
