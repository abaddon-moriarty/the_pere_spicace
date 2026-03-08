import sys
import asyncio
import logging
import sqlite3

from src.transcription_client.youtube_transcript_client import (
    get_transcription_youtube,
)

logger = logging.getLogger(__name__)


def initialise_database():
    sqlite_connection = sqlite3.connect("youtube_transcription_db.db")
    cursor = sqlite_connection.cursor()
    logger.warning("Initialising the database.")

    query = "SELECT sqlite_version();"
    cursor.execute(query)
    result = cursor.fetchall()
    logger.info(f"SQLite Version is {result}")

    cursor.execute("""
        SELECT count(name) FROM sqlite_master
        WHERE type='table' AND name='TRANSCRIPTIONS'
    """)

    if cursor.fetchone()[0] == 1:
        logger.warning("Table TRANSCRIPTIONS found.")
    else:
        logger.warning("Table TRANSCRIPTIONS not found, creating...")
        result = cursor.execute(
            """CREATE TABLE IF NOT EXISTS TRANSCRIPTIONS(
            video_id TEXT PRIMARY KEY AUTOINCREMENT,
            url VARCHAR(2048),
            transcript TEXT,
            title VARCHAR(512),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP);""",
        )
        sqlite_connection.commit()
        logger.warning("TRANSCRIPTIONS table created.")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    sqlite_connection.commit()
    sqlite_connection.close()


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


def check_retrieved_transcriptions(url):
    sqlite_connection = sqlite3.connect("youtube_transcription_db.db")
    cursor = sqlite_connection.cursor()
    try:
        result = cursor.execute(
            "SELECT transcript FROM TRANSCRIPTIONS WHERE url = ?;",
            (url,),
        ).fetchall()
        if result:
            return result
    except Exception:
        logger.exception(Exception)
        return None
    finally:
        sqlite_connection.close()


async def async_main(args):
    youtube_url = validate_youtube_url(args)

    transcript = check_retrieved_transcriptions(youtube_url)
    if check_retrieved_transcriptions(youtube_url):
        logger.info("Video already transcribed, pulling the transcription.")
        return transcript
    logger.info("Retrieving the transcription...")
    return await get_transcription_youtube(youtube_url)


def main(args):
    initialise_database()

    logger.info("Starting the Youtube learning pipeline")
    video_data = asyncio.run(async_main(args))

    logger.info(f"Got transcript: {video_data}")


if __name__ == "__main__":
    main(sys.argv)
