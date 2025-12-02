import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def display_tools(session: ClientSession):
    "Display available tools with non-clanker eyes"
    tools_response = await session.list_tools()

    for tool in tools_response.tools:
        display_name = tool.name
        print(f"Tool: {display_name}")
        if tool.description:
            print(f"    {tool.description}")


server_params = StdioServerParameters(
    command="docker",
    args=["run", "-i", "--rm", "mcp/youtube-transcript:latest"],
    env=None,
)


async def get_transcription_youtube(video_url: str):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print("=== Available Tools ===")
            await display_tools(session)

            result = await session.call_tool(
                name="get_transcript",
                arguments={"url": video_url},
            )

            full_transcript = ""
            has_more = True

            while has_more:
                for content in result.content:
                    if content.type == "text":
                        try:
                            data = json.loads(content.text)
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
                            print(f"Invalid JSON response: {content.text}")
                            return ""

                # Also check if result is an error
                if hasattr(result, "isError") and result.isError:
                    return ""

            return full_transcript
