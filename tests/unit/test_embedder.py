from unittest.mock import patch, MagicMock

import pytest

from src.rag.embedder import embedder


class TestEmbedder:
    @patch("rag.embedder.load_dotenv")
    @patch.dict("os.environ", {"EMBEDDING_MODEL": "test-model"})
    @patch("rag.embedder.ollama.embed")
    def test_embedder_with_valid_texts(self, mock_embed, _mock_dotenv):
        """Test embedder with valid text inputs."""
        mock_response = MagicMock()
        mock_response.embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_embed.return_value = mock_response

        result = embedder(["text1", "text2"])

        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_embed.assert_called_once_with(
            model="test-model",
            input=["text1", "text2"],
        )

    @patch("rag.embedder.load_dotenv")
    @patch.dict("os.environ", {"EMBEDDING_MODEL": "test-model"})
    def test_embedder_with_empty_list(self, _mock_dotenv):
        """
        Test embedder with empty text list
        returns early without calling ollama.
        """
        result = embedder([])
        assert result == []

    @patch("rag.embedder.load_dotenv")
    @patch.dict("os.environ", {"EMBEDDING_MODEL": "test-model"})
    @patch("rag.embedder.ollama.embed")
    def test_embedder_handles_exception(self, mock_embed, _mock_dotenv):
        """Test embedder re-raises exceptions from ollama."""
        mock_embed.side_effect = RuntimeError("Ollama connection failed")

        with pytest.raises(RuntimeError):
            embedder(["text1"])

    @patch("rag.embedder.load_dotenv")
    @patch.dict("os.environ", {"EMBEDDING_MODEL": "test-model"})
    @patch("rag.embedder.ollama.embed")
    def test_embedder_single_text(self, mock_embed, _mock_dotenv):
        """
        Test embedder with single text input returns a list of one vector.
        """
        mock_response = MagicMock()
        mock_response.embeddings = [[0.1, 0.2, 0.3]]
        mock_embed.return_value = mock_response

        result = embedder(["single text"])

        assert len(result) == 1
        assert result == [[0.1, 0.2, 0.3]]

    @patch("rag.embedder.load_dotenv")
    @patch.dict("os.environ", {"EMBEDDING_MODEL": "test-model"})
    @patch("rag.embedder.ollama.embed")
    def test_embedder_returns_correct_vector_count(
        self,
        mock_embed,
        _mock_dotenv,
    ):
        """
        Test that the number of returned vectors matches the number of inputs.
        """
        mock_response = MagicMock()
        mock_response.embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        mock_embed.return_value = mock_response

        result = embedder(["a", "b", "c"])

        assert len(result) == 3
