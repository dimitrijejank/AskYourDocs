from functools import lru_cache
from openai import OpenAI
from .config import get_settings

BATCH_SIZE = 64

@lru_cache
def _client() -> OpenAI:
    return OpenAI(api_key=get_settings().openai_api_key)

def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    settings = get_settings()
    vectors: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        response = _client().embeddings.create(
            model=settings.embedding_model,
            input=batch,
            dimensions=settings.embedding_dim
        )
        vectors.extend(item.embedding for item in sorted(response.data, key=lambda d: d.index))

    return vectors

def embed_query(text:str) -> list[float]:
    return embed([text])[0]
