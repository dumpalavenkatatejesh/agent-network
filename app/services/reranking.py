
from functools import lru_cache
from sentence_transformers import CrossEncoder
import math

from app.database.connection import settings


@lru_cache(maxsize=1)
def get_reranker():
    print("Loading cross-encoder model...")

    return CrossEncoder(
        settings.RERANKER_MODEL
    )


def rerank_agents(
    post_text: str,
    candidates: list,
) -> list[dict]:

    if not candidates:
        return []

    model = get_reranker()

    pairs = [
        (
            post_text,
            agent.interest_manifesto,
        )
        for agent, vector_score in candidates
    ]

    raw_scores = model.predict(pairs)

    results = []

    for (agent, vector_score), raw_score in zip(
        candidates,
        raw_scores,
    ):
        # Convert cross-encoder logit into a 0-1 score.
        raw_score = float(raw_score)

        if raw_score >= 0:
            rerank_score = 1 / (
                1 + math.exp(-raw_score)
            )
        else:
            exp_score = math.exp(raw_score)
            rerank_score = exp_score / (
                1 + exp_score
            )

        results.append({
            "agent": agent,
            "vector_score": float(vector_score),
            "rerank_score": rerank_score,
        })

    return sorted(
        results,
        key=lambda item: item["rerank_score"],
        reverse=True,
    )
