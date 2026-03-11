import sqlite3
import tempfile


from pathlib import Path

import pytest


@pytest.fixture
def temp_db_path():
    """Provide a temporary database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    path = Path(db_path)
    if path.exists():
        path.unlink()


@pytest.fixture
def temp_vault_dir(tmp_path):
    """Create a temporary Obsidian vault with sample markdown files."""
    vault = tmp_path / "vault"
    vault.mkdir()
    # Create a sample note
    note = vault / "note.md"
    note.write_text("""---
title: Test Note
tags: [python, testing]
last_enriched: 2023-01-01
domain: development
sources: https://example.com
---
This is the content of the test note.""")
    # Create a note in a subdirectory (excluded from Templates)
    sub = vault / "sub"
    sub.mkdir()
    (sub / "other.md").write_text("""---
title: Other
tags: []
---
Some content.""")
    # Create a Templates directory (should be ignored)
    templates = vault / "Templates"
    templates.mkdir()
    (templates / "template.md").write_text("Ignored template.")
    return str(vault)


@pytest.fixture
def mock_env_vars(monkeypatch, temp_vault_dir):
    """Set mock environment variables for testing."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", temp_vault_dir)
    monkeypatch.setenv("OLLAMA_MODEL", "test-model")
    monkeypatch.setenv("PROMPTS_DIR", str(Path(temp_vault_dir) / "prompts"))
    return monkeypatch


@pytest.fixture
def sample_transcript():
    """Return a sample transcript text."""
    return "This is a sample YouTube transcript.\
    It contains multiple sentences."


@pytest.fixture
def sample_url():
    """Return a sample YouTube URL."""
    return "https://www.youtube.com/watch?v=abc123"


@pytest.fixture
def mock_sqlite_connection(mocker):
    """Mock sqlite3.connect and cursor for database tests."""
    mock_conn = mocker.MagicMock(spec=sqlite3.Connection)
    mock_cursor = mocker.MagicMock(spec=sqlite3.Cursor)
    mock_conn.cursor.return_value = mock_cursor
    mocker.patch("sqlite3.connect", return_value=mock_conn)
    return mock_conn, mock_cursor


@pytest.fixture
def mock_mcp_session(mocker):
    """Mock the MCP client session for transcription tests."""
    mock_session = mocker.AsyncMock()
    mock_session.initialize = mocker.AsyncMock()
    mock_session.list_tools = mocker.AsyncMock()
    mock_session.call_tool = mocker.AsyncMock()
    return mock_session


@pytest.fixture
def mock_stdio_client(mocker, mock_mcp_session):
    """Mock stdio_client context manager to return mock session."""
    mock_read = mocker.MagicMock()
    mock_write = mocker.MagicMock()
    mock_cm = mocker.AsyncMock()
    mock_cm.__aenter__.return_value = (mock_read, mock_write)
    mock_stdio = mocker.patch(
        "transcription_client.youtube_transcription_client.stdio_client",
    )
    mock_stdio.return_value = mock_cm

    mock_session_cm = mocker.AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_mcp_session
    mocker.patch(
        "transcription_client.youtube_transcription_client.ClientSession",
        return_value=mock_session_cm,
    )
    return mock_stdio
