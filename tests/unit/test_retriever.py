from pathlib import Path
from unittest.mock import patch, MagicMock

from src.rag.retriever import ask

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_CHUNK = {
    "id": "note_chunk_0",
    "distance": 0.1,
    "document": "RAG stands for Retrieval Augmented Generation.",
    "metadata": {"source": "/vault/RAG.md"},
}


def _mock_settings(
    monkeypatch,
    model="llama3.2",
    prompts_dir="./prompts",
    chroma="./chroma_db",
):
    monkeypatch.setattr("src.config.settings.ollama_model", model)
    monkeypatch.setattr("src.config.settings.prompts_dir", Path(prompts_dir))
    monkeypatch.setattr(
        "src.config.settings.chroma_persist_path",
        Path(chroma),
    )
    # Reset the module-level VaultStore singleton
    # so each test gets a fresh mock
    monkeypatch.setattr("src.rag.retriever._store", None)


# ---------------------------------------------------------------------------
# Embedder failure
# ---------------------------------------------------------------------------


def test_ask_returns_message_if_embedding_fails(monkeypatch):
    _mock_settings(monkeypatch)
    with patch("src.rag.retriever.embedder", return_value=[]):
        result = ask("What is RAG?")
    assert "embed" in result.lower() or "could not" in result.lower()


# ---------------------------------------------------------------------------
# Empty ChromaDB results
# ---------------------------------------------------------------------------


def test_ask_returns_no_notes_message_when_no_results(monkeypatch):
    _mock_settings(monkeypatch)
    with (
        patch("src.rag.retriever.embedder", return_value=[[0.1, 0.2, 0.3]]),
        patch("src.rag.retriever.VaultStore") as mock_store,
    ):
        mock_store.return_value.query.return_value = []
        result = ask("What is the capital of Mars?")

    assert (
        "don't have notes" in result.lower()
        or result == "I don't have notes on that yet."
    )


# ---------------------------------------------------------------------------
# Happy path — LLM receives context and returns answer
# ---------------------------------------------------------------------------


def test_ask_returns_llm_answer(monkeypatch):
    _mock_settings(monkeypatch)

    fake_response = {
        "message": {"content": "RAG uses retrieval. [source: /vault/RAG.md]"},
    }
    mock_client = MagicMock()
    mock_client._load_prompt.return_value = (
        "You are a helpful assistant.",
        "Answer: {question}",
    )

    with (
        patch("src.rag.retriever.embedder", return_value=[[0.1, 0.2, 0.3]]),
        patch("src.rag.retriever.VaultStore") as mock_store,
        patch("src.rag.retriever.LLMClient", return_value=mock_client),
        patch("src.rag.retriever.ollama.chat", return_value=fake_response),
    ):
        mock_store.return_value.query.return_value = [FAKE_CHUNK]
        result = ask("What is RAG?")

    assert result == "RAG uses retrieval. [source: /vault/RAG.md]"


# ---------------------------------------------------------------------------
# Context is built correctly from results
# ---------------------------------------------------------------------------


def test_ask_builds_context_from_chunks(monkeypatch):
    _mock_settings(monkeypatch)

    chunks = [
        {
            "id": "a_0",
            "distance": 0.1,
            "document": "Chunk A content.",
            "metadata": {"source": "/vault/A.md"},
        },
        {
            "id": "b_0",
            "distance": 0.2,
            "document": "Chunk B content.",
            "metadata": {"source": "/vault/B.md"},
        },
    ]

    captured_messages: dict = {}
    fake_response = {"message": {"content": "answer"}}
    mock_client = MagicMock()
    mock_client._load_prompt.return_value = (
        "system",
        "user [source: /vault/A.md]\nChunk A content. test question",
    )

    def fake_chat(**kwargs):
        captured_messages["msgs"] = kwargs.get("messages", [])
        return fake_response

    with (
        patch("src.rag.retriever.embedder", return_value=[[0.0]]),
        patch("src.rag.retriever.VaultStore") as mock_store,
        patch("src.rag.retriever.LLMClient", return_value=mock_client),
        patch("src.rag.retriever.ollama.chat", side_effect=fake_chat),
    ):
        mock_store.return_value.query.return_value = chunks
        ask("test question")

    user_content = captured_messages["msgs"][1]["content"]
    assert "/vault/A.md" in user_content or "Chunk A" in user_content


# ---------------------------------------------------------------------------
# n_chunks parameter is forwarded to the store
# ---------------------------------------------------------------------------


def test_ask_passes_n_chunks_to_store(monkeypatch):
    _mock_settings(monkeypatch)

    fake_response = {"message": {"content": "some answer"}}
    mock_client = MagicMock()

    def fake_load_prompt(_name, **kwargs):
        return "system", f"user {kwargs['context']} {kwargs['question']}"

    mock_client._load_prompt.side_effect = fake_load_prompt

    with (
        patch("src.rag.retriever.embedder", return_value=[[0.0]]),
        patch("src.rag.retriever.VaultStore") as mock_store,
        patch("src.rag.retriever.LLMClient", return_value=mock_client),
        patch("src.rag.retriever.ollama.chat", return_value=fake_response),
    ):
        mock_store.return_value.query.return_value = [FAKE_CHUNK]
        ask("question", n_chunks=10)

    mock_store.return_value.query.assert_called_once_with(
        query_embedding=[0.0],
        n_results=10,
    )
