import sys
import logging


from pathlib import Path

import ollama

from src.config import settings
from src.rag.store import VaultStore
from src.rag.embedder import embedder
from src.llm.llm_client import LLMClient

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

_store: VaultStore | None = None


def _get_store() -> VaultStore:
    global _store
    if _store is None:
        _store = VaultStore(
            persist_path=settings.chroma_persist_path,
        )
    return _store


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    with path.open(encoding="utf-8") as f:
        return f.read()


def ask(question: str, n_chunks: int = 5, stream: bool = False) -> str:
    model_name = settings.ollama_model
    prompts_dir = settings.prompts_dir

    if model_name is None:
        msg = "OLLAMA_MODEL environment variable not set"
        raise ValueError(msg)

    # 1. Embed the question
    question_embeddings = embedder([question])
    if not question_embeddings:
        return "Could not embed the question."
    question_vector = question_embeddings[0]

    # 2. Query ChromaDB
    store = _get_store()
    results = store.query(query_embedding=question_vector, n_results=n_chunks)

    if not results:
        return "I don't have notes on that yet."

    # 3. Build context
    context = "\n\n".join(
        f"[source: {r['metadata'].get('source', 'unknown')}]\n{r['document']}"
        for r in results
    )

    # 4. Build prompt

    client = LLMClient(model_name=model_name, prompt_dir=prompts_dir)
    system_prompt, user_prompt = client._load_prompt(
        "retriever",
        context=context,
        question=question,
    )

    # 5. Call LLM
    response = ollama.chat(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        stream=stream,
    )

    return response["message"]["content"]


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    logging.basicConfig(level=logging.INFO)

    test_questions = [
        "What are the main differences between:\
            \nRAG and long context approache?",
        "How does median blur handle salt-and-pepper noise in OpenCV?",
        "What is the capital of Mars?",
    ]

    for q in test_questions:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Q: {q}")
        logger.info(f"{'=' * 60}")
        answer = ask(q)
        logger.info(f"A: {answer}")
