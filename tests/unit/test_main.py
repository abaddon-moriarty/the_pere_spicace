import sys


from unittest.mock import patch, AsyncMock

import pytest

from main import (
    main,
    async_main,
    validate_youtube_url,
    check_retrieved_transcriptions,
)


def test_validate_youtube_url_with_valid_arg():
    args = ["script.py", "https://youtube.com/watch?v=123"]
    result = validate_youtube_url(args)
    assert result == "https://youtube.com/watch?v=123"


def test_validate_youtube_url_with_invalid_then_valid(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "https://youtu.be/abc")
    args = ["script.py", "not a url"]
    result = validate_youtube_url(args)
    assert result == "https://youtu.be/abc"


def test_validate_youtube_url_no_arg(monkeypatch):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: "https://youtube.com/watch?v=xyz",
    )
    args = ["script.py"]
    result = validate_youtube_url(args)
    assert result == "https://youtube.com/watch?v=xyz"


def test_check_retrieved_transcriptions_found(mock_sqlite_connection):
    _, mock_cursor = mock_sqlite_connection
    mock_cursor.execute.return_value.fetchall.return_value = [("transcript",)]
    result = check_retrieved_transcriptions("http://url")
    assert result == [("transcript",)]


def test_check_retrieved_transcriptions_not_found(mock_sqlite_connection):
    _, mock_cursor = mock_sqlite_connection
    mock_cursor.execute.return_value.fetchall.return_value = []
    result = check_retrieved_transcriptions("http://url")
    assert result == []


@pytest.mark.asyncio
async def test_async_main_already_transcribed(mocker):
    mocker.patch("main.validate_youtube_url", return_value="http://url")
    mocker.patch(
        "main.check_retrieved_transcriptions",
        return_value=[("cached",)],
    )
    result = await async_main(["script.py"])
    assert result == [("cached",)]


@pytest.mark.asyncio
async def test_async_main_fetch_new(mocker):
    mocker.patch("main.validate_youtube_url", return_value="http://url")
    mocker.patch("main.check_retrieved_transcriptions", return_value=None)
    mock_get = mocker.patch(
        "main.get_transcription_youtube",
        new_callable=AsyncMock,
        return_value="new transcript",
    )
    result = await async_main(["script.py"])
    assert result == "new transcript"
    mock_get.assert_called_once_with("http://url")


@patch("main.build_vault_map")
@patch("main.initialise_database")
@patch("main.asyncio.run")
def test_main(mock_asyncio_run, mock_init_db, mock_build_vault):
    mock_build_vault.return_value = {"map": "data"}
    mock_asyncio_run.return_value = "transcript data"
    with patch("sys.argv", ["script.py", "https://youtube.com/watch?v=123"]):
        main(sys.argv)
    mock_build_vault.assert_called_once()
    mock_init_db.assert_called_once()
    mock_asyncio_run.assert_called_once()
