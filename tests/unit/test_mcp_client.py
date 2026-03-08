"""
Fixed unit tests for YouTube transcript client MCP integration.
"""

import json
import logging


from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from src.transcription_client.youtube_transcript_client import (
    display_tools,
    save_transcription_db,
    get_transcription_youtube,
)


@pytest.fixture(autouse=True)
def setup_logging(caplog):
    caplog.set_level(logging.INFO)


# Mock MCP types
class TextContent:
    def __init__(self, type="text", text=""):
        self.type = type
        self.text = text


class Tool:
    def __init__(self, name, description=None, inputSchema=None):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema


class ListToolsResult:
    def __init__(self, tools):
        self.tools = tools


class CallToolResult:
    def __init__(self, content, isError=False):
        self.content = content
        self.isError = isError


class TestSaveTranscriptionDb:
    """Test database save functionality."""

    def test_save_transcription_success(self):
        """Test successful transcription save."""
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            save_transcription_db(
                transcription="Test transcript",
                title="Test Title",
                url="https://youtube.com/test",
            )

            # Verify database operations
            mock_cursor.execute.assert_called_once()
            mock_conn.commit.assert_called_once()
            mock_conn.close.assert_called_once()


class TestDisplayTools:
    """Test the display_tools function."""

    @pytest.mark.asyncio
    async def test_display_tools_with_description(self, caplog):
        """Test displaying tools with descriptions."""
        mock_session = AsyncMock()
        mock_tools = [
            Tool(name="get_transcript", description="Get YouTube transcript"),
            Tool(name="other_tool", description="Another tool"),
        ]
        mock_response = ListToolsResult(tools=mock_tools)
        mock_session.list_tools.return_value = mock_response

        await display_tools(mock_session)

        assert "Tool: get_transcript" in caplog.text
        assert "Get YouTube transcript" in caplog.text


class TestGetTranscriptionYoutube:
    """Test the main transcription function."""

    @pytest.mark.asyncio
    async def test_successful_transcription_no_pagination(self):
        """Test successful transcription without pagination."""
        video_url = "https://www.youtube.com/watch?v=test123"
        expected_transcript = "This is the full transcript text."

        mock_json = json.dumps(
            {
                "title": "Test Video",
                "transcript": expected_transcript,
                "next_cursor": None,
            },
        )

        mock_content = [TextContent(type="text", text=mock_json)]
        mock_result = CallToolResult(content=mock_content, isError=False)

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        with (
            patch(
                "src.transcription_client.youtube_transcript_client.stdio_client",
            ) as mock_stdio,
            patch(
                "src.transcription_client.youtube_transcript_client.ClientSession",
            ) as mock_client,
            patch(
                "src.transcription_client.youtube_transcript_client.save_transcription_db",
            ),
        ):
            mock_stdio.return_value.__aenter__.return_value = (
                MagicMock(),
                MagicMock(),
            )
            mock_client.return_value.__aenter__.return_value = mock_session

            result = await get_transcription_youtube(video_url)

        assert result == expected_transcript

    @pytest.mark.asyncio
    async def test_transcription_with_pagination(self):
        """Test transcription with pagination."""
        video_url = "https://www.youtube.com/watch?v=longvideo"

        # First chunk with cursor
        first_json = json.dumps(
            {
                "title": "Long Video",
                "transcript": "First part ",
                "next_cursor": "cursor123",
            },
        )

        # Second chunk without cursor
        second_json = json.dumps(
            {
                "title": "Long Video",
                "transcript": "Second part.",
                "next_cursor": None,
            },
        )

        first_result = CallToolResult(
            content=[TextContent(type="text", text=first_json)],
            isError=False,
        )

        second_result = CallToolResult(
            content=[TextContent(type="text", text=second_json)],
            isError=False,
        )

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock()

        # Make call_tool return different results
        mock_session.call_tool = AsyncMock(
            side_effect=[first_result, second_result],
        )

        with (
            patch(
                "src.transcription_client.youtube_transcript_client.stdio_client",
            ) as mock_stdio,
            patch(
                "src.transcription_client.youtube_transcript_client.ClientSession",
            ) as mock_client,
            patch(
                "src.transcription_client.youtube_transcript_client.save_transcription_db",
            ),
        ):
            mock_stdio.return_value.__aenter__.return_value = (
                MagicMock(),
                MagicMock(),
            )
            mock_client.return_value.__aenter__.return_value = mock_session

            result = await get_transcription_youtube(video_url)

        assert result == "First part Second part."
        assert mock_session.call_tool.call_count == 2

    @pytest.mark.asyncio
    async def test_malformed_json_response(self):
        """Test handling of malformed JSON response."""
        video_url = "https://www.youtube.com/watch?v=malformed"

        # Non-JSON response
        malformed_content = TextContent(text="Not JSON at all", type="text")
        mock_result = CallToolResult(
            content=[malformed_content],
            isError=False,
        )

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        with (
            patch(
                "src.transcription_client.youtube_transcript_client.stdio_client",
            ) as mock_stdio,
            patch(
                "src.transcription_client.youtube_transcript_client.ClientSession",
            ) as mock_client,
        ):
            mock_stdio.return_value.__aenter__.return_value = (
                MagicMock(),
                MagicMock(),
            )
            mock_client.return_value.__aenter__.return_value = mock_session

            result = await get_transcription_youtube(video_url)

        # Should return empty string on JSON decode error
        assert result == ""

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry mechanism on failure."""
        video_url = "https://www.youtube.com/watch?v=retry"

        # First attempt fails, second succeeds
        error_result = CallToolResult(
            content=[
                TextContent(type="text", text='{"error": "Temporary error"}'),
            ],
            isError=True,
        )

        success_json = json.dumps(
            {
                "title": "Retry Video",
                "transcript": "Success after retry",
                "next_cursor": None,
            },
        )
        success_result = CallToolResult(
            content=[TextContent(type="text", text=success_json)],
            isError=False,
        )

        # Create separate mock sessions for each attempt
        mock_session_1 = AsyncMock()
        mock_session_1.initialize = AsyncMock()
        mock_session_1.list_tools = AsyncMock()
        mock_session_1.call_tool = AsyncMock(return_value=error_result)

        mock_session_2 = AsyncMock()
        mock_session_2.initialize = AsyncMock()
        mock_session_2.list_tools = AsyncMock()
        mock_session_2.call_tool = AsyncMock(return_value=success_result)

        with (
            patch(
                "src.transcription_client.youtube_transcript_client.stdio_client",
            ) as mock_stdio,
            patch(
                "src.transcription_client.youtube_transcript_client.ClientSession",
            ) as mock_client,
            patch(
                "src.transcription_client.youtube_transcript_client.save_transcription_db",
            ),
            patch("asyncio.sleep"),  # Speed up test by mocking sleep
        ):
            # Setup context managers for both attempts
            mock_stdio_ctx_1 = MagicMock()
            mock_stdio_ctx_1.__aenter__ = AsyncMock(
                return_value=(MagicMock(), MagicMock()),
            )
            mock_stdio_ctx_1.__aexit__ = AsyncMock()

            mock_stdio_ctx_2 = MagicMock()
            mock_stdio_ctx_2.__aenter__ = AsyncMock(
                return_value=(MagicMock(), MagicMock()),
            )
            mock_stdio_ctx_2.__aexit__ = AsyncMock()

            mock_stdio.side_effect = [mock_stdio_ctx_1, mock_stdio_ctx_2]

            mock_client_ctx_1 = MagicMock()
            mock_client_ctx_1.__aenter__ = AsyncMock(
                return_value=mock_session_1,
            )
            mock_client_ctx_1.__aexit__ = AsyncMock()

            mock_client_ctx_2 = MagicMock()
            mock_client_ctx_2.__aenter__ = AsyncMock(
                return_value=mock_session_2,
            )
            mock_client_ctx_2.__aexit__ = AsyncMock()

            mock_client.side_effect = [mock_client_ctx_1, mock_client_ctx_2]

            result = await get_transcription_youtube(video_url)

        assert result == "Success after retry"

    @pytest.mark.asyncio
    async def test_empty_transcript(self):
        """Test handling of empty transcript."""
        video_url = "https://www.youtube.com/watch?v=empty"

        mock_json = json.dumps(
            {
                "title": "Empty Video",
                "transcript": "",
                "next_cursor": None,
            },
        )

        mock_result = CallToolResult(
            content=[TextContent(type="text", text=mock_json)],
            isError=False,
        )

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        with (
            patch(
                "src.transcription_client.youtube_transcript_client.stdio_client",
            ) as mock_stdio,
            patch(
                "src.transcription_client.youtube_transcript_client.ClientSession",
            ) as mock_client,
            patch(
                "src.transcription_client.youtube_transcript_client.save_transcription_db",
            ),
        ):
            mock_stdio.return_value.__aenter__.return_value = (
                MagicMock(),
                MagicMock(),
            )
            mock_client.return_value.__aenter__.return_value = mock_session

            result = await get_transcription_youtube(video_url)

        assert result == ""
