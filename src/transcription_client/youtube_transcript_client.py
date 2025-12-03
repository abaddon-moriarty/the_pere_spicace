import json
import time
import asyncio
import logging
import secrets
import sqlite3

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


server_params = StdioServerParameters(
    command="docker",
    args=["run", "-i", "--rm", "mcp/youtube-transcript:latest"],
    env=None,
)


def save_transcription_db(transcription, title, url):
    sqlite_connection = sqlite3.connect("youtube_transcription_db.db")
    cursor = sqlite_connection.cursor()
    cursor.execute(
        """INSERT INTO TRANSCRIPTIONS
                   (url, transcript, title, timestamp)
                   VALUES (?, ?, ?, ?);
                   """,
        (url, transcription, title, time.time()),
    )
    sqlite_connection.commit()
    sqlite_connection.close()
    return


async def display_tools(session: ClientSession):
    "Display available tools with non-clanker eyes"
    tools_response = await session.list_tools()
    logger.info("=== Available Tools ===")

    for tool in tools_response.tools:
        display_name = tool.name
        logger.info(f"Tool: {display_name}")
        if tool.description:
            logger.info(f"    {tool.description}")


async def get_transcription_youtube(video_url: str):
    """
    Retrieves the transcription of the youtube video through
    mcp-youtube-transcription repo.
    Loop for mulitple attemps.
    """
    max_attempts = 3
    for attempt in range(max_attempts):
        logger.warning(
            f"YouTube Transcription MCP connexion attempt: {attempt}",
        )
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # await display_tools(session)

                    result = await session.call_tool(
                        name="get_transcript",
                        arguments={"url": video_url},
                    )
                    title = ""
                    full_transcript = ""
                    has_more = True

                    while has_more:
                        for content in result.content:
                            if content.type == "text":
                                try:
                                    data = json.loads(content.text)
                                    title = data.get("title", "")
                                    transcription = data.get("transcript", "")
                                    full_transcript += transcription

                                    next_cursor = data.get("next_cursor")
                                    if next_cursor:
                                        result = await session.call_tool(
                                            name="get_transcript",
                                            arguments={
                                                "url": video_url,
                                                "next_cursor": next_cursor,
                                            },
                                        )
                                    else:
                                        has_more = False
                                except json.JSONDecodeError:
                                    print(
                                        f"Invalid JSON response: {content.text}",
                                    )
                                    return ""

                        # Also check if result is an error
                        if hasattr(result, "isError") and result.isError:
                            # Check if it's a 429 error
                            error_text = ""
                            if result.content:
                                for content in result.content:
                                    if content.type == "text":
                                        error_text = content.text

                            if (
                                "429" in error_text
                                or "Too Many Requests" in error_text
                            ):
                                raise Exception(
                                    f"YouTube rate limit: {error_text}",
                                )
                            raise Exception(f"MCP error: {error_text}")
                save_transcription_db(full_transcript, title, video_url)
                return full_transcript
        except Exception as e:
            logger.exception(
                f"Attempt {attempt} failed with error: {type(e).__name__}: {e}",
            )
            if attempt == max_attempts - 1:
                raise
            delay = (2 ^ attempt) ** secrets.randbelow(3)
            logger.info(f"Waiting {delay} seconds before retry...")
            await asyncio.sleep(delay)
    return ""
