"""
Unit tests for main.py functionality.
"""

from unittest.mock import patch, AsyncMock, MagicMock

import pytest

# Import functions to test
from main import main, async_main, validate_youtube_url


# Add at the top of your test file
@pytest.fixture(autouse=True)
def mock_transcription():
    """Mock the entire transcription client to avoid real API calls."""
    with (
        patch(
            "src.transcription_client.youtube_transcript_client.stdio_client",
        ) as mock_stdio,
        patch(
            "src.transcription_client.youtube_transcript_client.ClientSession",
        ) as mock_client,
    ):
        # Create a mock session
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock()

        # Mock successful response
        mock_content = MagicMock()
        mock_content.type = "text"
        mock_content.text = (
            '{"transcript": "Mock transcript text", "next_cursor": null}'
        )

        mock_result = MagicMock()
        mock_result.content = [mock_content]
        mock_result.isError = False

        mock_session.call_tool = AsyncMock(return_value=mock_result)

        # Setup context manager mocks
        mock_stdio.return_value.__aenter__.return_value = (
            MagicMock(),
            MagicMock(),
        )
        mock_client.return_value.__aenter__.return_value = mock_session

        yield


class TestValidateYoutubeUrl:
    """Test URL validation functionality."""

    def test_valid_youtube_url_from_args(self):
        """Test valid YouTube URL from command line arguments."""
        test_args = ["main.py", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]

        with patch("sys.argv", test_args):
            result = validate_youtube_url(test_args)

        assert result == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_valid_youtube_short_url(self):
        """Test valid YouTube short URL."""
        test_args = ["main.py", "https://youtu.be/dQw4w9WgXcQ"]

        with patch("sys.argv", test_args):
            result = validate_youtube_url(test_args)

        assert result == "https://youtu.be/dQw4w9WgXcQ"

    def test_invalid_url(self, capsys):
        """Test invalid URL triggers correction."""
        test_args = ["main.py", "https://example.com/not-youtube"]

        # Mock input to return valid URL after invalid one
        input_responses = [
            "https://example.com/another-invalid",
            "https://www.youtube.com/watch?v=valid",
        ]
        with patch("builtins.input", side_effect=input_responses):
            with patch("sys.argv", test_args):
                result = validate_youtube_url(test_args)

        captured = capsys.readouterr()
        assert "This is not a youtube url." in captured.out
        assert result == "https://www.youtube.com/watch?v=valid"

    def test_no_url_provided(self, capsys):
        """Test when no URL is provided in args."""
        test_args = ["main.py"]

        with (
            patch(
                "builtins.input",
                return_value="https://www.youtube.com/watch?v=test123",
            ),
            patch("sys.argv", test_args),
        ):
            result = validate_youtube_url(test_args)

        captured = capsys.readouterr()
        # FIXED: Removed debug print statement
        assert "Youtube url recognised" in captured.out
        assert result == "https://www.youtube.com/watch?v=test123"


class TestAsyncMain:
    """Test async main functionality."""

    @pytest.mark.asyncio
    async def test_async_main_success(self, mock_transcription):
        """Test successful async main execution."""
        test_args = ["main.py", "https://www.youtube.com/watch?v=test123"]

        # Mock validate_youtube_url to return URL
        with patch("main.validate_youtube_url", return_value=test_args[1]):
            result = await async_main(test_args)

        # Should get the mock transcript from the fixture
        assert "Mock transcript text" in result

    @pytest.mark.asyncio
    async def test_async_main_url_validation(self, mock_transcription):
        """Test URL validation within async_main."""
        test_args = ["main.py", "invalid-url"]

        # Mock validate_youtube_url to return valid URL
        with patch(
            "main.validate_youtube_url",
            return_value="https://www.youtube.com/watch?v=valid",
        ):
            result = await async_main(test_args)

        assert "Mock transcript text" in result


class TestMainFunction:
    """Test the main function integration."""

    def test_main_success(self, capsys):
        """Test successful main function execution."""
        test_args = ["main.py", "https://www.youtube.com/watch?v=test123"]
        mock_transcript = "Sample transcript text."

        # Mock asyncio.run to avoid the event loop conflict
        with patch("asyncio.run") as mock_run:
            mock_run.return_value = mock_transcript
            with patch("sys.argv", test_args):
                main(test_args)

        captured = capsys.readouterr()
        assert "Starting the Youtube learning pipeline" in captured.out
        # Don't assert async_main outputs since we're mocking asyncio.run

    def test_main_empty_transcript(self, capsys):
        """Test main function with empty transcript."""
        test_args = ["main.py", "https://www.youtube.com/watch?v=empty"]

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = ""
            with patch("sys.argv", test_args):
                main(test_args)

        captured = capsys.readouterr()
        assert "Starting the Youtube learning pipeline" in captured.out


# Test the __main__ guard indirectly
def test_module_can_be_imported():
    """Test that the module can be imported without side effects."""
    import main

    assert hasattr(main, "main")
    assert hasattr(main, "validate_youtube_url")
    assert hasattr(main, "async_main")
