
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.feedback import Feedback


def recalculate_trust_score(
    db: Session,
    agent_id,
) -> float:

    agent = db.get(Agent, agent_id)

    if agent is None:
        raise ValueError("Agent not found")

    feedbacks = (
        db.query(Feedback)
        .filter(Feedback.agent_id == agent_id)
        .all()
    )

    positive = sum(
        1 for item in feedbacks
        if item.feedback_type in ["RELEVANT", "USEFUL"]
    )

    negative = sum(
        1 for item in feedbacks
        if item.feedback_type in ["IRRELEVANT", "NOT_USEFUL"]
    )

    # Start at 0.5 and adjust by 0.05 per net positive feedback.
    score = 0.5 + 0.05 * (positive - negative)

    # Keep score within the range 0.0 to 1.0.
    score = max(0.0, min(1.0, score))

    agent.trust_score = round(score, 4)

    return agent.trust_score
