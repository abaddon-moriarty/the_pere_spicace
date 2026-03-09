import sys
import asyncio
import logging
import sqlite3


from typing import Any

from src.database.sqlite_memory import initialise_database
from src.obsidian.vault_structure import build_vault_map
from src.transcription_client.youtube_transcript_client import (
    get_transcription_youtube,
)

logger = logging.getLogger(__name__)


def validate_youtube_url(args):
    try:
        youtube_url = args[1]
        logger.info(f"The url is: {youtube_url}")
    except IndexError:
        youtube_url = input("Please provide a youtube url: \n")

    # Keep asking until valid URL
    while not any(
        domain in youtube_url for domain in ["youtube.com", "youtu.be"]
    ):
        logger.warning("This is not a youtube url.")
        youtube_url = input("Please provide a valid youtube url: \n")

    logger.info("Youtube url recognised")
    return youtube_url


def check_retrieved_transcriptions(url: str) -> list[Any] | None:
    sqlite_connection = sqlite3.connect("youtube_transcription_db.db")
    cursor = sqlite_connection.cursor()
    try:
        result = cursor.execute(
            "SELECT transcript FROM TRANSCRIPTIONS WHERE url = ?;",
            (url,),
        ).fetchall()
        return result if result else []  # return empty list if no rows
    except Exception:
        logger.exception("Database error")
        return None
    finally:
        sqlite_connection.close()


async def async_main(args):
    youtube_url = validate_youtube_url(args)

    transcript = check_retrieved_transcriptions(youtube_url)
    if transcript:
        logger.info("Video already transcribed, pulling the transcription.")
        return transcript
    logger.info("Retrieving the transcription...")
    return await get_transcription_youtube(youtube_url)


def main(args):
    vault_map = build_vault_map()  # currently unused, will be used later

    initialise_database()

    logger.info("Starting the Youtube learning pipeline.")
    video_data = asyncio.run(async_main(args))

    logger.info(f"Got transcript: {video_data}")


if __name__ == "__main__":
    main(sys.argv)
