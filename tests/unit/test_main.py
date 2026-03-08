"""
Unit tests for main.py functionality.
"""

import logging


from unittest.mock import patch

import pytest

# Import functions to test
from main import (
    main,
    async_main,
    validate_youtube_url,
    check_retrieved_transcriptions,
)


@pytest.fixture(autouse=True)
def setup_logging(caplog):
    caplog.set_level(logging.INFO)


class TestValidateYoutubeUrl:
    """Test URL validation functionality."""

    def test_valid_youtube_url_from_args(self):
        """Test valid YouTube URL from command line arguments."""
        test_args = ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
        result = validate_youtube_url(test_args)
        assert result == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_valid_youtube_short_url(self):
        """Test valid YouTube short URL."""
        test_args = ["main.py", "https://youtu.be/dQw4w9WgXcQ"]
        result = validate_youtube_url(test_args)
        assert result == "https://youtu.be/dQw4w9WgXcQ"

    def test_invalid_url(self, caplog):
        """Test invalid URL triggers correction."""
        test_args = ["main.py", "https://example.com/not-youtube"]

        # Mock input to return valid URL after invalid one
        input_responses = [
            "https://example.com/another-invalid",
            "https://www.youtube.com/watch?v=valid",
        ]
        with patch("builtins.input", side_effect=input_responses):
            result = validate_youtube_url(test_args)

        assert "This is not a youtube url." in caplog.text
        assert result == "https://www.youtube.com/watch?v=valid"

    def test_no_url_provided(self, caplog):
        """Test when no URL is provided in args."""
        test_args = ["main.py"]

        with patch(
            "builtins.input",
            return_value="https://www.youtube.com/watch?v=test123",
        ):
            result = validate_youtube_url(test_args)

        assert "Youtube url recognised" in caplog.text
        assert result == "https://www.youtube.com/watch?v=test123"


class TestCheckRetrievedTranscriptions:
    """Test database retrieval functionality."""

    def test_check_existing_transcription(self, mock_database):
        """Test retrieving an existing transcription."""
        test_url = "https://www.youtube.com/watch?v=test123"
        expected_transcript = "Existing transcript"

        # Configure mock to return a transcript
        mock_database.cursor().fetchall.return_value = [(expected_transcript,)]

        result = check_retrieved_transcriptions(test_url)

        assert result == [(expected_transcript,)]

    def test_check_no_transcription(self, mock_database):
        """Test when no transcription exists."""
        test_url = "https://www.youtube.com/watch?v=new_video"

        # Configure mock to return empty
        mock_database.cursor().fetchall.return_value = []

        result = check_retrieved_transcriptions(test_url)

        assert result is None

    def test_check_database_error(self, mock_database):
        """Test handling of database errors."""
        test_url = "https://www.youtube.com/watch?v=error"

        # Configure mock to raise an exception
        mock_database.cursor().execute.side_effect = Exception(
            "Database error",
        )

        result = check_retrieved_transcriptions(test_url)

        assert result is None


class TestAsyncMain:
    """Test async main functionality."""

    @pytest.mark.asyncio
    async def test_async_main_new_video(
        self,
        mock_database,
        mock_transcription_client,
    ):
        """Test async main with a new video (not in database)."""
        test_args = ["main.py", "https://www.youtube.com/watch?v=test123"]

        # Configure mock to return no existing transcript
        mock_database.cursor().fetchall.return_value = []

        result = await async_main(test_args)

        assert "Mock transcript text" in result

    @pytest.mark.asyncio
    async def test_async_main_existing_video(self, mock_database):
        """Test async main with existing video in database."""
        test_args = ["main.py", "https://www.youtube.com/watch?v=existing"]
        existing_transcript = [("Cached transcript from database",)]

        # Configure mock to return existing transcript
        mock_database.cursor().fetchall.return_value = existing_transcript

        result = await async_main(test_args)

        assert result == existing_transcript

    @pytest.mark.asyncio
    async def test_async_main_url_validation(self, mock_database):
        """Test URL validation within async_main."""
        test_args = ["main.py", "invalid-url"]

        # Mock input to provide valid URL
        with patch(
            "builtins.input",
            return_value="https://www.youtube.com/watch?v=valid",
        ):
            result = await async_main(test_args)

        assert "Mock transcript text" in result


class TestMainFunction:
    """Test the main function integration."""

    def test_main_success(self, caplog, mock_database):
        """Test successful main function execution."""
        test_args = ["main.py", "https://www.youtube.com/watch?v=test123"]
        mock_transcript = "Sample transcript text."

        # Mock asyncio.run to avoid the event loop conflict
        with patch("asyncio.run") as mock_run:
            mock_run.return_value = mock_transcript
            main(test_args)

        assert "Starting the Youtube learning pipeline" in caplog.text
        assert "Got transcript:" in caplog.text

    def test_main_empty_transcript(self, caplog, mock_database):
        """Test main function with empty transcript."""
        test_args = ["main.py", "https://www.youtube.com/watch?v=empty"]

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = ""
            main(test_args)

        assert "Starting the Youtube learning pipeline" in caplog.text

    def test_main_database_initialization(self, mock_database):
        """Test that database is initialized on main call."""
        test_args = ["main.py", "https://www.youtube.com/watch?v=test"]

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = "transcript"
            main(test_args)

        # Verify database connection was created
        mock_database.cursor.assert_called()


# Test the __main__ guard indirectly
def test_module_can_be_imported():
    """Test that the module can be imported without side effects."""
    import main

    assert hasattr(main, "main")
    assert hasattr(main, "validate_youtube_url")
    assert hasattr(main, "async_main")
    assert hasattr(main, "check_retrieved_transcriptions")
    assert hasattr(main, "initialise_database")
