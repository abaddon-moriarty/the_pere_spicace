"""
Pytest configuration and fixtures.
"""

import json


from unittest.mock import patch, AsyncMock, MagicMock

import pytest


# Mock classes for MCP types
class TextContent:
    def __init__(self, type, text):
        self.type = type
        self.text = text


class CallToolResult:
    def __init__(self, content, isError=False):
        self.content = content
        self.isError = isError


class Tool:
    def __init__(self, name, description=None, inputSchema=None):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema


class ListToolsResult:
    def __init__(self, tools):
        self.tools = tools


@pytest.fixture
def mock_mcp_response():
    """Fixture for creating mock MCP responses."""

    def _create_response(
        transcript_text, title="Test Video", next_cursor=None, is_error=False
    ):
        response_data = {
            "title": title,
            "transcript": transcript_text,
            "next_cursor": next_cursor,
        }

        content = [TextContent(type="text", text=json.dumps(response_data))]
        return CallToolResult(content=content, isError=is_error)

    return _create_response


@pytest.fixture
def mock_database():
    """Mock the database to avoid file I/O during tests."""
    with patch("sqlite3.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Default behavior: table exists, no transcripts found
        mock_cursor.fetchone.return_value = [1]  # Table exists
        mock_cursor.fetchall.return_value = []  # No transcripts
        mock_cursor.execute.return_value = mock_cursor

        mock_conn.cursor.return_value = mock_cursor
        mock_conn.commit.return_value = None
        mock_conn.close.return_value = None

        mock_connect.return_value = mock_conn

        yield mock_conn


@pytest.fixture(autouse=True)
def mock_transcription_client():
    """Mock the entire transcription client to avoid real API calls."""
    with (
        patch(
            "src.transcription_client.youtube_transcript_client.stdio_client"
        ) as mock_stdio,
        patch(
            "src.transcription_client.youtube_transcript_client.ClientSession"
        ) as mock_client,
    ):
        # Create a mock session
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock()

        # Mock successful response
        mock_content = TextContent(
            type="text",
            text='{"title": "Test Video", "transcript": "Mock transcript text", "next_cursor": null}',
        )

        mock_result = CallToolResult(content=[mock_content], isError=False)
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        # Setup context manager mocks
        mock_stdio.return_value.__aenter__.return_value = (
            MagicMock(),
            MagicMock(),
        )
        mock_client.return_value.__aenter__.return_value = mock_session

        yield mock_session
