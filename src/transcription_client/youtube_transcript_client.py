import json
import asyncio
import logging
import secrets


from typing import Any, cast
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.database.sqlite_memory import save_transcription_db
from src.utils.cookie_extractor import get_brave_cookies

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class CookieDecryptionError(Exception):
    pass


class YouTubeRateLimitError(Exception):
    pass


class MCPError(Exception):
    pass


def _raise_mcp_error(error_text: str) -> None:
    if "cannot decrypt v11 cookies: no key found" in error_text:
        msg = f"Cookies could not be decrypted: {error_text}"
        raise CookieDecryptionError(msg)
    if "429" in error_text or "Too Many Requests" in error_text:
        msg = f"YouTube rate limit: {error_text}"
        raise YouTubeRateLimitError(msg)
    msg = f"MCP error: {error_text}"
    raise MCPError(msg)


server_configs: list[dict[str, Any]] = [
    {
        "name": "brave",
        "params": StdioServerParameters(
            command="npx",
            args=["-y", "@kevinwatt/yt-dlp-mcp"],
            env={
                "YTDLP_COOKIES_FROM_BROWSER": (
                    "brave:~/.var/app/com.brave.Browser/"
                ),
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


async def display_tools(session: ClientSession):
    """Display available tools with non-clanker eyes"""
    tools_response = await session.list_tools()
    logger.info("=== Available Tools ===")
    for tool in tools_response.tools:
        logger.info(f"Tool: {tool.name}")
        if tool.description:
            logger.info(f"    {tool.description}")


async def get_transcription_youtube(video_url: str):
    """
    Retrieves the transcription of the youtube video through yt-dlp-mcp.
    Handles ExceptionGroup from MCP client and unwraps single exceptions.
    """
    for config in server_configs:
        logger.info(f"Trying with {config['name']}...")
        # Cast to StdioServerParameters to help mypy
        server_params = cast("StdioServerParameters", config["params"])
        max_attempts = 2

        for attempt in range(max_attempts):
            logger.warning(
                f"YouTube Transcription yt-dlp-mcp MCP connexion attempt:\
                    {attempt + 1}",
            )

            try:
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()

                        await display_tools(session)

                        transcription_result = await session.call_tool(
                            name="ytdlp_download_transcript",
                            arguments={"url": video_url},
                        )

                        if (
                            hasattr(transcription_result, "isError")
                            and transcription_result.isError
                        ):
                            error_text = ""
                            if transcription_result.content:
                                for content in transcription_result.content:
                                    if content.type == "text":
                                        error_text = content.text
                            _raise_mcp_error(error_text)

                        full_transcript = ""
                        for content in transcription_result.content:
                            if content.type == "text":
                                full_transcript = content.text

                        metadata_result = await session.call_tool(
                            name="ytdlp_get_video_metadata",
                            arguments={"url": video_url, "fields": ["title"]},
                        )
                        logger.debug(f"Metadata result: {metadata_result}")

                        title = ""
                        if metadata_result.content:
                            for content in metadata_result.content:
                                if content.type == "text":
                                    try:
                                        data = json.loads(content.text)
                                        title = data.get("title", "")
                                        # assuming the first text content
                                        # contains the metadata
                                        break
                                    except json.JSONDecodeError:
                                        logger.exception(
                                            "Failed to parse metadata JSON",
                                        )
                                        continue

                    try:
                        logger.info("Saving transcription")
                        save_transcription_db(
                            full_transcript,
                            title,
                            video_url,
                        )
                    except Exception:
                        logger.exception(
                            "Could not save transcription to db",
                        )

            except CookieDecryptionError:
                # Direct CookieDecryptionError (rare)
                logger.warning("Cookie decryption error (direct)...")
                await _handle_cookie_error(video_url)
                # Continue to next attempt

            except ExceptionGroup as eg:
                # Unwrap single exception if possible
                if len(eg.exceptions) == 1:
                    inner_ex = eg.exceptions[0]
                    if isinstance(inner_ex, CookieDecryptionError):
                        logger.warning("Cookie decryption error (in group)...")
                        await _handle_cookie_error(video_url)
                    elif isinstance(
                        inner_ex,
                        (YouTubeRateLimitError, MCPError),
                    ):
                        raise inner_ex from eg
                    else:
                        # Unknown exception, re-raise group
                        raise
                else:
                    # Multiple exceptions
                    # check for CookieDecryptionError inside
                    for ex in eg.exceptions:
                        if isinstance(ex, CookieDecryptionError):
                            logger.warning(
                                "Cookie decryption error\
                                    (in group with others)",
                            )
                            await _handle_cookie_error(video_url)
                            break
                    else:
                        # No cookie error, re-raise group
                        raise

            except Exception:
                logger.exception(
                    f"Attempt {attempt} failed with error",
                )
                if attempt == max_attempts - 1:
                    raise
                delay = (2**attempt) * max(secrets.randbelow(3), 1)
                logger.info(f"Waiting {delay} seconds before retry...")
                await asyncio.sleep(delay)

            else:
                return full_transcript
    return ""


async def _handle_cookie_error(video_url: str):
    """Helper to extract cookies and update config for next attempt."""
    try:
        get_brave_cookies(video_url)
        cookie_path = Path("cookies.txt").resolve()
        # Update the cookies_file config
        # cast to StdioServerParameters
        cookies_config = cast(
            "StdioServerParameters",
            server_configs[1]["params"],
        )
        cookies_config.args = [
            "-y",
            "@kevinwatt/yt-dlp-mcp",
            "--",
            "yt-dlp",
            "--cookies",
            str(cookie_path),
        ]
        logger.info(
            f"Cookies extracted to {cookie_path}. Retry with cookies file.",
        )
    except Exception:
        logger.exception("Cookie extraction failed")
