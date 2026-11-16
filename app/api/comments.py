
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.engagement import Engagement
from app.models.comment import Comment
from app.models.post import Post
from app.models.agent import Agent
from app.schemas.comment import CommentResponse
from app.services.comment_generator import generate_comment_draft

router = APIRouter(
    prefix="/api/v1/comments",
    tags=["Comments"],
)


@router.post(
    "/draft/{engagement_id}",
    response_model=CommentResponse,
)
def create_comment_draft(
    engagement_id: UUID,
    db: Session = Depends(get_db),
):
    # 1. Find engagement
    engagement = db.get(Engagement, engagement_id)

    if engagement is None:
        raise HTTPException(404, "Engagement not found")

    # 2. Only ENGAGE decisions can generate comments
    if engagement.decision != "ENGAGE":
        raise HTTPException(
            400,
            "Agent must choose ENGAGE before generating a comment",
        )

    # 3. Get post and agent
    post = db.get(Post, engagement.post_id)
    agent = db.get(Agent, engagement.agent_id)

    if post is None or agent is None:
        raise HTTPException(404, "Post or agent not found")

    # 4. Check for an existing comment
    comment = (
        db.query(Comment)
        .filter(Comment.engagement_id == engagement.id)
        .first()
    )

    if comment and comment.status == "PUBLISHED":
        raise HTTPException(
            409,
            "This engagement already has a published comment",
        )

    # 5. Generate draft using Ollama
    try:
        draft = generate_comment_draft(
            post_title=post.title,
            post_content=post.content,
            company_name=agent.company_name,
            industry_category=agent.industry_category,
            interest_manifesto=agent.interest_manifesto,
        )
    except Exception as error:
        raise HTTPException(
            502,
            detail=f"Comment generation failed: {str(error)}",
        )

    # 6. Save or update draft
    if comment is None:
        comment = Comment(
            engagement_id=engagement.id,
            content=draft,
            status="DRAFT",
        )
        db.add(comment)
    else:
        comment.content = draft
        comment.status = "DRAFT"

    db.commit()
    db.refresh(comment)

    return comment


@router.post(
    "/{comment_id}/publish",
    response_model=CommentResponse,
)
def publish_comment(
    comment_id: UUID,
    db: Session = Depends(get_db),
):
    comment = db.get(Comment, comment_id)

    if comment is None:
        raise HTTPException(404, "Comment not found")

    if comment.status == "PUBLISHED":
        raise HTTPException(
            409,
            "Comment is already published",
        )

    comment.status = "PUBLISHED"
    comment.published_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(comment)

    return comment


@router.get(
    "/{comment_id}",
    response_model=CommentResponse,
)
def get_comment(
    comment_id: UUID,
    db: Session = Depends(get_db),
):
    comment = db.get(Comment, comment_id)

    if comment is None:
        raise HTTPException(404, "Comment not found")

    return comment
