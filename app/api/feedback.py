
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.agent import Agent
from app.models.post import Post
from app.models.notification import Notification
from app.models.feedback import Feedback
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.services.trust_score import recalculate_trust_score

router = APIRouter(
    prefix="/api/v1/feedback",
    tags=["Feedback"],
)


@router.post("/", response_model=FeedbackResponse, status_code=201)
def submit_feedback(
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
):
    # Verify post
    post = db.get(Post, payload.post_id)

    if post is None:
        raise HTTPException(404, "Post not found")

    # Verify active agent
    agent = db.get(Agent, payload.agent_id)

    if agent is None or not agent.is_active:
        raise HTTPException(404, "Active agent not found")

    # Only notified agents can provide feedback
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
            403,
            "Agent was not selected to receive this post",
        )

    # Create or update feedback
    feedback = (
        db.query(Feedback)
        .filter(
            Feedback.post_id == payload.post_id,
            Feedback.agent_id == payload.agent_id,
        )
        .first()
    )

    if feedback is None:
        feedback = Feedback(
            post_id=payload.post_id,
            agent_id=payload.agent_id,
            rating=payload.rating,
            feedback_type=payload.feedback_type,
            comment=payload.comment,
        )
        db.add(feedback)
    else:
        feedback.rating = payload.rating
        feedback.feedback_type = payload.feedback_type
        feedback.comment = payload.comment

    # Save feedback changes before calculating the score
    db.flush()

# Recalculate the agent's trust score
    new_trust_score = recalculate_trust_score(
    db,
    payload.agent_id,
    )

    print("Updated agent trust score:", new_trust_score)

# Save feedback and trust score together
    db.commit()
    db.refresh(feedback)

    return feedback


@router.get("/{agent_id}/summary")
def get_feedback_summary(
    agent_id: UUID,
    db: Session = Depends(get_db),
):
    agent = db.get(Agent, agent_id)

    if agent is None:
        raise HTTPException(404, "Agent not found")

    feedbacks = (
        db.query(Feedback)
        .filter(Feedback.agent_id == agent_id)
        .all()
    )

    total = len(feedbacks)

    if total == 0:
        return {
            "agent_id": str(agent_id),
            "total_feedback": 0,
            "average_rating": None,
            "positive_feedback": 0,
            "negative_feedback": 0,
        }

    positive = sum(
        1 for item in feedbacks
        if item.feedback_type in ["RELEVANT", "USEFUL"]
    )

    negative = sum(
        1 for item in feedbacks
        if item.feedback_type in ["IRRELEVANT", "NOT_USEFUL"]
    )

    return {
        "agent_id": str(agent_id),
        "total_feedback": total,
        "average_rating": round(
            sum(item.rating for item in feedbacks) / total, 2
        ),
        "positive_feedback": positive,
        "negative_feedback": negative,
    }
