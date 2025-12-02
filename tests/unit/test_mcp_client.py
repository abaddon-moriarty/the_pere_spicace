"""
Fixed unit tests for YouTube transcript client MCP integration.
"""

import os
import sys
import json


from unittest.mock import patch, AsyncMock, MagicMock

import pytest

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Create proper mock classes that match what your function expects
class MockTextContent:
    def __init__(self, text, type="text"):
        self.type = type
        self.text = text


class MockCallToolResult:
    def __init__(self, text_content, isError=False):
        self.content = (
            text_content if isinstance(text_content, list) else [text_content]
        )
        self.isError = isError


# Mock MCP types - KEEP THESE HERE (don't import from conftest)
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


# Import after setting up mocks
try:
    from src.transcription_client.youtube_transcript_client import (
        display_tools,
        get_transcription_youtube,
    )
except ImportError:
    # Try alternative import path
    from src.transcription_client.youtube_transcript_client import (
        display_tools,
        get_transcription_youtube,
    )


class TestDisplayTools:
    """Test the display_tools function."""

    @pytest.mark.asyncio
    async def test_display_tools_with_description(self, capsys):
        """Test displaying tools with descriptions."""
        mock_session = AsyncMock()
        mock_tools = [
            Tool(name="get_transcript", description="Get transcript"),
            Tool(name="other_tool", description="Another tool"),
        ]
        mock_response = ListToolsResult(tools=mock_tools)
        mock_session.list_tools.return_value = mock_response

        await display_tools(mock_session)

        captured = capsys.readouterr()
        assert "Tool: get_transcript" in captured.out


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

        # Mock context managers
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

        assert result == expected_transcript

    @pytest.mark.asyncio
    async def test_error_response(self):
        """Test handling of error response from MCP server."""
        video_url = "https://www.youtube.com/watch?v=error"

        # Create error response that matches what your function expects
        error_content = MockTextContent(
            text='{"error": "Video not found", "transcript": ""}',
            type="text",
        )
        error_result = MockCallToolResult(error_content, isError=True)

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=error_result)

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

            from src.transcription_client.youtube_transcript_client import (
                get_transcription_youtube,
            )

            result = await get_transcription_youtube(video_url)

        # Should return empty string on error
        assert result == ""

    @pytest.mark.asyncio
    async def test_transcription_with_pagination(self):
        """Test transcription with pagination."""
        video_url = "https://www.youtube.com/watch?v=longvideo"

        # First chunk with cursor
        first_json = json.dumps(
            {
                "transcript": "First part ",
                "next_cursor": "cursor123",
            },
        )

        # Second chunk without cursor
        second_json = json.dumps(
            {
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
        call_count = 0

        async def call_tool_side_effect(name, arguments):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return first_result
            return second_result

        mock_session.call_tool = AsyncMock(side_effect=call_tool_side_effect)

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

        assert result == "First part Second part."
        assert mock_session.call_tool.call_count == 2

    @pytest.mark.asyncio
    async def test_malformed_json_response(self):
        """Test handling of malformed JSON response."""
        video_url = "https://www.youtube.com/watch?v=malformed"

        # Non-JSON response that will cause JSONDecodeError
        malformed_content = MockTextContent(
            text="Not JSON at all",
            type="text",
        )
        mock_result = MockCallToolResult(malformed_content, isError=False)

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

            from src.transcription_client.youtube_transcript_client import (
                get_transcription_youtube,
            )

            # This should handle the JSON decode error gracefully
            result = await get_transcription_youtube(video_url)

        # The implementation now returns empty string for all JSON decode errors
        assert result == ""

    @pytest.mark.asyncio
    async def test_empty_transcript(self):
        """Test handling of empty transcript."""
        video_url = "https://www.youtube.com/watch?v=empty"

        mock_json = json.dumps(
            {
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
        ):
            mock_stdio.return_value.__aenter__.return_value = (
                MagicMock(),
                MagicMock(),
            )
            mock_client.return_value.__aenter__.return_value = mock_session

            result = await get_transcription_youtube(video_url)

        # FIXED: Should return empty string, not "Not JSON at all"

        assert result == ""
