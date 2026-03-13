"""

Build the prompt — assemble a string that contains: a system instruction telling the LLM to answer only from the provided context, then each retrieved chunk (with its source filename as a label), then the question. Format matters here — experiment with this.
Call Ollama — send the prompt to llama3.2 via ollama.chat(). Return the response text.
"""

import os
import sys
import logging


from pathlib import Path

import ollama


from dotenv import load_dotenv

from src.rag.store import VaultStore
from src.rag.embedder import embedder
from src.llm.llm_client import LLMClient

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    with path.open(encoding="utf-8") as f:
        return f.read()


def ask(question: str, n_chunks: int = 5) -> str:
    load_dotenv()
    model = os.getenv("OLLAMA_MODEL")
    prompts_dir = Path(os.getenv("PROMPTS_DIR", "./prompts"))
    chroma_path = os.getenv("CHROMA_DB_PATH", "./chroma_db")

    # 1. Embed the question
    question_embeddings = embedder([question])
    if not question_embeddings:
        return "Could not embed the question."
    question_vector = question_embeddings[0]

    # 2. Query ChromaDB
    store = VaultStore(persist_path=chroma_path)
    results = store.query(query_embedding=question_vector, n_results=n_chunks)

    if not results:
        return "I don't have notes on that yet."

    # 3. Build context
    context = "\n\n".join(
        f"[source: {r['metadata'].get('source', 'unknown')}]\n{r['document']}"
        for r in results
    )

    # 4. Build prompt

    client = LLMClient(model_name=model, prompt_dir=prompts_dir)
    system_prompt, user_prompt = client._load_prompt(
        "retriever",
        context=context,
        question=question,
    )

    # 5. Call LLM
    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response["message"]["content"]


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    logging.basicConfig(level=logging.INFO)

    test_questions = [
        "What are the main differences between RAG and long context approaches?",
        "How does median blur handle salt-and-pepper noise in OpenCV?",
        "What is the capital of Mars?",
    ]

    for q in test_questions:
        print(f"\n{'=' * 60}")
        print(f"Q: {q}")
        print(f"{'=' * 60}")
        answer = ask(q)
        print(f"A: {answer}")
