import sys
import asyncio

from src.transcription_client.youtube_transcript_client import (
    get_transcription_youtube,
)


def validate_youtube_url(args):
    try:
        youtube_url = args[1]
        print(f"The url is: {youtube_url}")
    except IndexError:
        youtube_url = input("Please provide a youtube url: \n")

    # Keep asking until valid URL
    while not any(
        domain in youtube_url for domain in ["youtube.com", "youtu.be"]
    ):
        print("This is not a youtube url.")
        youtube_url = input("Please provide a valid youtube url: \n")

    print("Youtube url recognised")
    return youtube_url


async def async_main(args):
    youtube_url = validate_youtube_url(args)

    print("Retrieving the transcription...")
    transcript = await get_transcription_youtube(youtube_url)
    return transcript


def main(args):
    print("Starting the Youtube learning pipeline")
    video_data = asyncio.run(async_main(args))

    print(f"Got transcript: {video_data}")


if __name__ == "__main__":
    main(sys.argv)
