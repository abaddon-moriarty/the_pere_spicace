import os
import json
import asyncio
import logging
import secrets

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from database.sqlite_memory import save_transcription_db
from utils.cookie_extractor import get_brave_cookies

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class CookieDecryptionError(Exception):
    """Raised when browser cookies cannot be decrypted."""


# server_params = StdioServerParameters(
#     command="docker",
#     args=["run", "-i", "--rm", "mcp/youtube-transcript:latest"],
#     env=None,
# )

server_params = StdioServerParameters(
    command="npx",
    args=[
        "-y",
        "@kevinwatt/yt-dlp-mcp",
    ],
)

server_configs = [
    {
        "name": "brave",
        "params": StdioServerParameters(
            command="npx",
            args=["-y", "@kevinwatt/yt-dlp-mcp"],
            env={
                "YTDLP_COOKIES_FROM_BROWSER": "brave:~/.var/app/com.brave.Browser/",
            },
        ),
    },
    {
        "name": "cookies_file",
        "params": StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "@kevinwatt/yt-dlp-mcp",
                "--",
                "yt-dlp",
                "--cookies",
                "./src/utils/cookies.txt",
            ],
        ),
    },
]

# https://youtu.be/E9h8qVm2uNY?si=rL3l_MCLbOZq0yZ7


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
    Retrieves the transcription of the youtube video through yt-dlp-mcp
    Loop for multiple attempts.
    """
    for config in server_configs:
        logger.info(f"Trying with {config['name']}...")
        server_params = config["params"]
        max_attempts = 2  # per configuration

        for attempt in range(max_attempts):
            logger.warning(
                f"YouTube Transcription yt-dlp-mcp MCP connexion attempt: {attempt + 1}",
            )

            try:
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()

                        # await display_tools(session)

                        transcription_result = await session.call_tool(
                            name="ytdlp_download_transcript",
                            arguments={
                                "url": video_url,
                                #    "language": "", #
                            },
                        )

                        # Handle MCP error immediately
                        if (
                            hasattr(transcription_result, "isError")
                            and transcription_result.isError
                        ):
                            error_text = ""
                            if transcription_result.content:
                                for content in transcription_result.content:
                                    if content.type == "text":
                                        error_text = content.text

                            if (
                                "cannot decrypt v11 cookies: no key found"
                                in error_text
                            ):
                                raise CookieDecryptionError(
                                    f"Cookies could not be decrypted: {error_text}",
                                )

                            if (
                                "429" in error_text
                                or "Too Many Requests" in error_text
                            ):
                                raise Exception(
                                    f"YouTube rate limit: {error_text}",
                                )

                            raise Exception(f"MCP error: {error_text}")

                        title = ""
                        full_transcript = ""

                        for content in transcription_result.content:
                            if content.type == "text":
                                full_transcript = content.text

                        metadata_result = await session.call_tool(
                            name="ytdlp_get_video_metadata",
                            arguments={
                                "url": video_url,
                                "fields": ["title"],
                            },
                        )
                        print(metadata_result)

                        title = ""
                        if metadata_result.content:
                            for content in metadata_result.content:
                                if content.type == "text":
                                    try:
                                        data = json.loads(content.text)
                                        title = data.get("title", "")

                                        break  # assuming the first text content contains the metadata
                                    except json.JSONDecodeError:
                                        logger.exception(
                                            "Failed to parse metadata JSON",
                                        )
                                        continue

                    try:
                        print("Saving transcription")
                        save_transcription_db(
                            full_transcript,
                            title,
                            video_url,
                        )

                    except Exception as e:
                        print(f"Could not save transcription to db: {e}")

                return full_transcript

            except CookieDecryptionError:
                logger.warning(
                    "Cookies could not be decrypted. Extracting cookies to Netscape format...",
                )
                try:
                    get_brave_cookies(video_url)  # this creates cookies.txt
                    # Update the cookies_file config with the actual path
                    cookie_path = os.path.abspath("cookies.txt")
                    server_configs[1]["params"].args = [
                        "-y",
                        "@kevinwatt/yt-dlp-mcp",
                        "--",
                        "yt-dlp",
                        "--cookies",
                        cookie_path,
                    ]
                    logger.info(
                        f"Cookies extracted to {cookie_path}. Will try with cookies file.",
                    )
                except Exception as ex:
                    logger.exception(f"Cookie extraction failed: {ex}")

            except Exception as ex:
                logger.exception(
                    f"Attempt {attempt} failed with error: {type(ex).__name__}: {ex}",
                )

                if attempt == max_attempts - 1:
                    raise
                delay = (2**attempt) * max(secrets.randbelow(3), 1)
                logger.info(f"Waiting {delay} seconds before retry...")
                await asyncio.sleep(delay)
    return ""
