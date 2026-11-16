
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.agent import Agent
from app.models.post import Post
from app.models.notification import Notification
from app.models.engagement import Engagement
from app.schemas.engagement import (
    EngagementCreate,
    EngagementResponse,
)

router = APIRouter(
    prefix="/api/v1/engagements",
    tags=["Engagements"],
)


@router.post("/", response_model=EngagementResponse)
def create_engagement(
    payload: EngagementCreate,
    db: Session = Depends(get_db),
):
    # 1. Check whether the post exists
    post = db.get(Post, payload.post_id)

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    # 2. Check whether the agent exists and is active
    agent = db.get(Agent, payload.agent_id)

    if agent is None or not agent.is_active:
        raise HTTPException(
            status_code=404,
            detail="Active agent not found",
        )

    # 3. Only notified agents can engage
    notification = (
        db.query(Notification)
        .filter(
            Notification.post_id == payload.post_id,
            Notification.target_agent_id == payload.agent_id,
        )
        .first()
    )

    if notification is None:
        raise HTTPException(
            status_code=403,
            detail="This agent was not selected to receive this post",
        )

    # 4. Check for an existing engagement
    engagement = (
        db.query(Engagement)
        .filter(
            Engagement.post_id == payload.post_id,
            Engagement.agent_id == payload.agent_id,
        )
        .first()
    )

    # 5. Create or update the engagement
    if engagement is None:
        engagement = Engagement(
            post_id=payload.post_id,
            agent_id=payload.agent_id,
            decision=payload.decision,
            reason=payload.reason,
        )
        db.add(engagement)
    else:
        engagement.decision = payload.decision
        engagement.reason = payload.reason

    db.commit()
    db.refresh(engagement)

    return engagement


@router.get("/{engagement_id}", response_model=EngagementResponse)
def get_engagement(
    engagement_id: UUID,
    db: Session = Depends(get_db),
):
    engagement = db.get(Engagement, engagement_id)

    if engagement is None:
        raise HTTPException(
            status_code=404,
            detail="Engagement not found",
        )

    return engagement
