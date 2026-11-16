from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
)


class AgentCreate(BaseModel):
    company_name: str = Field(
        min_length=2,
        max_length=255,
    )

    industry_category: str = Field(
        min_length=2,
        max_length=100,
    )

    webhook_url: HttpUrl

    interest_manifesto: str = Field(
        min_length=10,
        max_length=5000,
    )


class AgentResponse(BaseModel):
    id: UUID
    company_name: str
    industry_category: str
    webhook_url: str
    interest_manifesto: str
    trust_score: float
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )