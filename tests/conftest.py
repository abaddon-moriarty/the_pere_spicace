"""
Pytest configuration and fixtures.
"""

import json

import pytest


# Mock classes for MCP types
# Note: These are available to all tests via conftest, but should NOT be imported
# Pytest loads conftest.py automatically - it's not a regular module
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

    def _create_response(transcript_text, next_cursor=None, is_error=False):
        response_data = {
            "transcript": transcript_text,
            "next_cursor": next_cursor,
        }

        content = [TextContent(type="text", text=json.dumps(response_data))]
        return CallToolResult(content=content, isError=is_error)

    return _create_response
