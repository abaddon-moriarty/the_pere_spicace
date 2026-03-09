from main import check_retrieved_transcriptions
from src.database.sqlite_memory import (
    initialise_database,
    save_transcription_db,
)


def test_initialise_database_creates_table(mock_sqlite_connection):
    mock_conn, mock_cursor = mock_sqlite_connection
    # Simulate table not found
    mock_cursor.fetchone.return_value = [0]

    initialise_database()

    mock_cursor.execute.assert_any_call("""
        SELECT count(name) FROM sqlite_master
        WHERE type='table' AND name='TRANSCRIPTIONS'
    """)
    mock_cursor.execute.assert_any_call(
        """CREATE TABLE IF NOT EXISTS TRANSCRIPTIONS(
            video_id INTEGER PRIMARY KEY AUTOINCREMENT,
            url VARCHAR(2048),
            transcript TEXT,
            title VARCHAR(512),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
    )
    mock_conn.commit.assert_called()
    mock_conn.close.assert_called()


def test_initialise_database_table_exists(mock_sqlite_connection):
    mock_conn, mock_cursor = mock_sqlite_connection
    mock_cursor.fetchone.return_value = [1]  # table exists

    initialise_database()

    # Should not attempt to create table
    create_calls = [
        call
        for call in mock_cursor.execute.call_args_list
        if "CREATE TABLE" in str(call)
    ]
    assert len(create_calls) == 0
    mock_conn.close.assert_called()


def test_save_transcription_db(mock_sqlite_connection):
    mock_conn, _ = mock_sqlite_connection
    url = "http://test.com"
    transcript = "test transcript"
    title = "Test Title"

    save_transcription_db(transcript, title, url)

    mock_conn.execute.assert_called_once_with(
        """INSERT INTO TRANSCRIPTIONS
                   (url, transcript, title)
                   VALUES (?, ?, ?);
                   """,
        (url, transcript, title),
    )
    mock_conn.commit.assert_called()
    mock_conn.close.assert_called()


def test_check_retrieved_transcriptions_found(mock_sqlite_connection):
    mock_conn, mock_cursor = mock_sqlite_connection
    url = "http://test.com"
    expected = [("some transcript",)]
    mock_cursor.execute.return_value.fetchall.return_value = expected

    result = check_retrieved_transcriptions(url)

    mock_cursor.execute.assert_called_once_with(
        "SELECT transcript FROM TRANSCRIPTIONS WHERE url = ?;",
        (url,),
    )
    assert result == expected
    mock_conn.close.assert_called()


def test_check_retrieved_transcriptions_not_found(mock_sqlite_connection):
    mock_conn, mock_cursor = mock_sqlite_connection
    url = "http://test.com"
    mock_cursor.execute.return_value.fetchall.return_value = []

    result = check_retrieved_transcriptions(url)

    assert result == []
    mock_conn.close.assert_called()


def test_check_retrieved_transcriptions_exception(
    mock_sqlite_connection,
    caplog,
):
    mock_conn, mock_cursor = mock_sqlite_connection
    mock_cursor.execute.side_effect = Exception("DB error")

    result = check_retrieved_transcriptions("http://test.com")

    assert result is None
    mock_conn.close.assert_called()
    assert "DB error" in caplog.text
