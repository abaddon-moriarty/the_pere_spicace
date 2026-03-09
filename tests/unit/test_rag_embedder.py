from unittest.mock import patch, MagicMock

from src.rag.embedder import embedder


@patch("src.rag.embedder.ollama.embed")
def test_embedder(mock_ollama_embed):
    mock_response = MagicMock()
    mock_response.embeddings = [[0.1, 0.2], [0.3, 0.4]]
    mock_ollama_embed.return_value = mock_response

    texts = ["hello", "world"]
    result = embedder(texts)

    mock_ollama_embed.assert_called_once_with(
        model="qwen3-embedding:4b",
        input=texts,
    )
    assert result == [[0.1, 0.2], [0.3, 0.4]]
