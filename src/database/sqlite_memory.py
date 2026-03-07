import logging
import sqlite3

logger = logging.getLogger(__name__)


def initialise_database():
    sqlite_connection = sqlite3.connect("youtube_transcription_db.db")
    cursor = sqlite_connection.cursor()
    logger.info("Initialising the database.")

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
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS TRANSCRIPTIONS(
            video_id INTEGER PRIMARY KEY AUTOINCREMENT,
            url VARCHAR(2048),
            transcript TEXT,
            title VARCHAR(512),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
        )
        sqlite_connection.commit()
        logger.warning("TRANSCRIPTIONS table created.")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    sqlite_connection.commit()
    sqlite_connection.close()


def save_transcription_db(transcription, title, url):
    sqlite_connection = sqlite3.connect("youtube_transcription_db.db")
    sqlite_connection.execute(
        """INSERT INTO TRANSCRIPTIONS
                   (url, transcript, title)
                   VALUES (?, ?, ?);
                   """,
        (url, transcription, title),
    )

    sqlite_connection.commit()
    sqlite_connection.close()
    return
