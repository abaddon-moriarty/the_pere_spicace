import os


from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.utils.cookie_extractor import get_brave_cookies


@patch("utils.cookie_extractor.Path.exists")
@patch("utils.cookie_extractor.sqlite3.connect")
def test_get_brave_cookies_success(mock_connect, mock_exists, tmp_path):
    mock_exists.return_value = True
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # Mock fetchall to return some cookies
    mock_cursor.fetchall.return_value = [
        {
            "host_key": ".youtube.com",
            "path": "/",
            "is_secure": 1,
            "expires_utc": 123456,
            "name": "SESSIONID",
            "value": "abc123",
            "is_httponly": 1,
        },
    ]
    # Create the required subdirectory in the temporary directory
    (tmp_path / "src" / "utils").mkdir(parents=True)

    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        get_brave_cookies("https://www.youtube.com/watch?v=abc")
    finally:
        os.chdir(original_cwd)

    mock_connect.assert_called_once()
    mock_cursor.execute.assert_called_once()
    cookie_file = tmp_path / "src" / "utils" / "cookies.txt"
    assert cookie_file.exists()
    content = cookie_file.read_text()
    assert "SESSIONID" in content
    assert "abc123" in content


@patch("utils.cookie_extractor.Path.exists")
def test_get_brave_cookies_db_not_found(mock_exists):
    mock_exists.return_value = False
    with pytest.raises(
        FileNotFoundError,
        match="Brave cookies database not found",
    ):
        get_brave_cookies("https://www.youtube.com/watch?v=abc")
