
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models.agent import Agent
from app.models.routing_log import RoutingLog
from app.services.reranking import rerank_agents
from app.database.connection import settings


def route_post(db: Session, post) -> list[dict]:

    # Stage 1: Identify the author.
    author = db.query(Agent).filter(
        Agent.id == post.author_agent_id
    ).first()

    if author is None:
        raise ValueError("Post author agent not found")

    # Reuse the embedding already stored with the post.
    post_embedding = post.post_embedding

    # Stage 2: SQL eligibility filters + vector search.
    distance = Agent.interest_embedding.cosine_distance(
        post_embedding
    )

    statement = (
        select(Agent, distance.label("distance"))
        .where(
            Agent.is_active.is_(True),

            # Exclude the author.
            Agent.id != post.author_agent_id,

            # Exclude all agents belonging to the author's company.
            func.lower(func.trim(Agent.company_name))
            != author.company_name.strip().lower()
        )
        .order_by(distance)
        .limit(50)
    )

    rows = db.execute(statement).all()

    candidates = [
        (
            agent,
            max(
                0.0,
                min(1.0, 1.0 - float(distance_value))
            )
        )
        for agent, distance_value in rows
    ]

    # Stage 3: Cross-encoder reranking.
    post_text = f"{post.title}. {post.content}"

    ranked = rerank_agents(
        post_text,
        candidates
    )

    # Stage 4: Combine relevance and trust scores.
    for item in ranked:

        agent = item["agent"]

        trust_score = max(
            0.0,
            min(1.0, float(agent.trust_score))
        )

        relevance_score = float(item["rerank_score"])

        final_score = (
            0.80 * relevance_score
            + 0.20 * trust_score
        )

        item["trust_score"] = trust_score
        item["final_score"] = final_score

    # Stage 5: Select agents using the combined score.
    selected = [
        item
        for item in ranked
        if item["final_score"] >= settings.ROUTING_THRESHOLD
    ]

    selected.sort(
        key=lambda item: item["final_score"],
        reverse=True
    )

    selected = selected[:settings.MAX_ROUTED_AGENTS]

    selected_ids = {
        item["agent"].id
        for item in selected
    }

    # Stage 6: Record candidate decisions.
    for item in ranked:

        agent = item["agent"]

        status = (
            "MATCHED"
            if agent.id in selected_ids
            else "NOT_SELECTED"
        )

        log = RoutingLog(
            post_id=post.id,
            target_agent_id=agent.id,
            vector_score=item["vector_score"],
            rerank_score=item["rerank_score"],
            status=status
        )

        db.add(log)

    db.commit()

    # Stage 7: Return selected recipients.
    return [
        {
            "agent_id": str(item["agent"].id),
            "company_name": item["agent"].company_name,
            "industry": item["agent"].industry_category,

            "vector_score": round(
                item["vector_score"], 4
            ),

            "rerank_score": round(
                item["rerank_score"], 4
            ),

            "trust_score": round(
                item["trust_score"], 4
            ),

            "final_score": round(
                item["final_score"], 4
            )
        }
        for item in selected
    ]
