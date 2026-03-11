import sqlite3

import pytest

from main import check_retrieved_transcriptions
from src.database.sqlite_memory import (
    initialise_database,
    save_transcription_db,
)


def test_save_and_retrieve_transcription(
    temp_db_path,
    sample_url,
    sample_transcript,
):
    # Override database path
    # (need to modify module to use a test path, or mock)
    # For integration, we can patch sqlite3.connect to use temp_db_path
    original_connect = sqlite3.connect

    def test_connect(*args, **kwargs):
        if args and args[0] == "youtube_transcription_db.db":
            return original_connect(temp_db_path)
        return original_connect(*args, **kwargs)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sqlite3, "connect", test_connect)
        # Re-import modules or patch the ones already imported
        # Simpler: call functions after patching
        initialise_database()
        save_transcription_db(sample_transcript, "Test Title", sample_url)

        result = check_retrieved_transcriptions(sample_url)
        assert result is not None
        assert result[0][0] == sample_transcript
