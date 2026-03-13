import logging


from collections.abc import Sequence

import ollama

from src.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def embedder(texts: list) -> list[Sequence[float]]:
    """
    Convert a list of text strings into embeddings using Ollama.

    Args:
        texts (list): List of strings to embed.

    Returns:
        list[list[float]]: List of embedding vectors, one per input text.
    """

    model = settings.ollama_embed_model
    if not model:
        msg = "EMBEDDING_MODEL not set"
        raise ValueError(msg)
    logger.info(
        f"Embedding with model '{model}'",
    )
    logger.info(
        f"Embedding {len(texts)} text chunk(s)",
    )
    if not texts:
        logger.warning(
            "No texts provided for embedding; returning empty list.",
        )
        return []

    try:
        response = ollama.embed(
            model=model,
            input=texts,
        )
        embeddings = response.embeddings
        logger.debug(
            f"Received embeddings of dimension{
                len(embeddings[0]) if embeddings else 0
            }",
        )
    except Exception:
        logger.exception("Embedding failed")
        raise
    else:
        return list(embeddings)
