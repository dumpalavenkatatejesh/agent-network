from functools import lru_cache
from sentence_transformers import SentenceTransformer

from app.database.connection import settings


@lru_cache(maxsize=1)
def get_embedding_model():
    print("Loading embedding model...")

    return SentenceTransformer(
        settings.EMBEDDING_MODEL
    )


def generate_embedding(text: str) -> list[float]:
    model = get_embedding_model()

    embedding = model.encode(
        text,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    return embedding.tolist()