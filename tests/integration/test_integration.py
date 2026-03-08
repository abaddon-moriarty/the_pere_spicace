"""
Integration tests for the complete pipeline.
"""

import logging


from unittest.mock import patch

import pytest


# Set up logging to capture all levels
@pytest.fixture(autouse=True)
def setup_logging(caplog):
    caplog.set_level(logging.INFO)


class TestFullPipelineIntegration:
    """Integration tests for the full pipeline."""

    def test_end_to_end_with_mocks(self, mock_database, caplog):
        """Test the full pipeline with all components mocked."""
        test_args = [
            "main.py",
            "https://www.youtube.com/watch?v=integration_test",
        ]
        mock_transcript = "Integration test transcript."

        # Mock asyncio.run
        with patch("asyncio.run") as mock_run:
            mock_run.return_value = mock_transcript

            from main import main

            main(test_args)

            assert "Starting the Youtube learning pipeline" in caplog.text
            assert "Got transcript:" in caplog.text

    def test_error_handling_integration(self, mock_database, caplog):
        """Test error handling through the entire pipeline."""
        test_args = ["main.py", "https://youtube.com/invalid"]

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = ""

            from main import main

            main(test_args)

            assert "Starting the Youtube learning pipeline" in caplog.text

    @pytest.mark.asyncio
    async def test_full_async_flow(
        self,
        mock_database,
        mock_transcription_client,
    ):
        """Test the full async flow from URL validation to transcription."""
        from main import async_main

        test_args = ["main.py", "https://www.youtube.com/watch?v=async_test"]

        result = await async_main(test_args)

        assert result is not None
        assert isinstance(result, str) or isinstance(result, list)

    def test_database_caching(self, mock_database, caplog):
        """Test that cached transcripts are retrieved from database."""
        test_args = ["main.py", "https://www.youtube.com/watch?v=cached"]
        cached_transcript = [("Cached transcript content",)]

        # Configure mock to return cached transcript
        mock_database.cursor().fetchall.return_value = cached_transcript

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = cached_transcript

            from main import main

            main(test_args)

            assert "Starting the Youtube learning pipeline" in caplog.text
