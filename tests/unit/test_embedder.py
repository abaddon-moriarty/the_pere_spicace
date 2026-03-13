from unittest.mock import patch, MagicMock

import pytest

from src.rag.embedder import embedder


class TestEmbedder:
    def test_embedder_with_valid_texts(self, monkeypatch):
        """Test embedder with valid text inputs."""
        monkeypatch.setattr(
            "src.config.settings.ollama_embed_model",
            "test-model",
        )
        mock_response = MagicMock()
        mock_response.embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        with patch(
            "src.rag.embedder.ollama.embed",
            return_value=mock_response,
        ) as mock_embed:
            result = embedder(["text1", "text2"])
        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_embed.assert_called_once_with(
            model="test-model",
            input=["text1", "text2"],
        )

    def test_embedder_with_empty_list(self, monkeypatch):
        """
        Test embedder with empty text list
        returns early without calling ollama.
        """
        monkeypatch.setattr(
            "src.config.settings.ollama_embed_model",
            "test-model",
        )
        result = embedder([])
        assert result == []

    def test_embedder_handles_exception(self, monkeypatch):
        """Test embedder re-raises exceptions from ollama."""
        monkeypatch.setattr(
            "src.config.settings.ollama_embed_model",
            "test-model",
        )
        with (
            patch(
                "src.rag.embedder.ollama.embed",
                side_effect=RuntimeError("connection failed"),
            ),
            pytest.raises(RuntimeError),
        ):
            embedder(["text1"])

    def test_embedder_single_text(self, monkeypatch):
        """
        Test embedder with single text input returns a list of one vector.
        """
        monkeypatch.setattr(
            "src.config.settings.ollama_embed_model",
            "test-model",
        )
        mock_response = MagicMock()
        mock_response.embeddings = [[0.1, 0.2, 0.3]]
        with patch(
            "src.rag.embedder.ollama.embed",
            return_value=mock_response,
        ):
            result = embedder(["single text"])
        assert result == [[0.1, 0.2, 0.3]]

    def test_embedder_returns_correct_vector_count(self, monkeypatch):
        """
        Test that the number of returned vectors matches the number of inputs.
        """
        monkeypatch.setattr(
            "src.config.settings.ollama_embed_model",
            "test-model",
        )
        mock_response = MagicMock()
        mock_response.embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        with patch(
            "src.rag.embedder.ollama.embed",
            return_value=mock_response,
        ):
            result = embedder(["a", "b", "c"])
        assert len(result) == 3
