import re
import logging


from pathlib import Path

import frontmatter

from rag.embedder import embedder

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def chunker(note_name: str) -> list[dict]:
    """
    This function reads a markdown file with YAML frontmatter, extracts
    the content, and splits it into chunks organized by heading hierarchy.
    Each chunk preserves context by including the previous section's ending
    (last 200 characters) along with the current paragraph content.

    Args:
        note_name (str): File path to the markdown note to be chunked.

    Returns:
        list[dict]: A list of chunk dictionaries, each containing:
            - heading (str): The heading under which this chunk falls
            - content (str): The chunk content with previous section context
            - source (str): The source file path
            - index (int): The sequential index of the chunk

    Raises:
        FileNotFoundError: If the note file does not exist
        frontmatter.ParserError: If the frontmatter cannot be parsed

    Notes:
        - Processes only the first 50 sections of the document
        - Splits large sections (>2000 chars) into paragraph chunks
        - Ignores paragraphs with 50 characters or fewer
        - Preserves 200 characters from the previous section for context
    """
    logger.info(f"Starting chunking for file: {note_name}")

    try:
        with Path(note_name).open(encoding="utf-8") as file:
            post = frontmatter.load(file)
            body = post.content
        logger.debug(
            f"Frontmatter loaded, content length: {len(body)} characters",
        )
    except FileNotFoundError:
        logger.exception(f"File not found: {note_name}")
        raise
    except frontmatter.ParserError:
        logger.exception(f"Failed to parse frontmatter in {note_name}")
        raise

    sections = re.split(r"(\#+.*)", body)
    logger.info(
        f"Split document into {len(sections)}\
            raw sections (processing first 50)",
    )

    chunks = []
    previous_section = ""
    current_heading = ""

    for section in sections:
        if not section:
            continue

        # CASE 1: Section is a heading line (starts with #)
        if re.match(r"#+.*", section):
            current_heading = section.strip()
            logger.debug(f"Heading found: {current_heading}")
            previous_section = section.strip()[-200:]
            continue

        # CASE 2: Section is content
        # If content is too long, split into smaller paragraphs
        if len(section) > 2000:
            paragraphs = section.split("\n\n")
            logger.debug(
                f"Large section ({len(section)} chars) split into\
                    {len(paragraphs)} paragraphs",
            )
        else:
            paragraphs = [section]

        for para in paragraphs:
            para = para.strip()
            if not para or len(para) <= 50:
                logger.debug(f"Skipping short paragraph ({len(para)} chars)")
                continue

            chunk = {
                "heading": current_heading,
                "content": f"{previous_section}\n{para}",
                "source": note_name,
            }
            chunks.append(chunk)
            logger.debug(
                f"Created chunk under heading '{current_heading}'\
                    with {len(chunk['content'])} chars",
            )

            # Update previous_section with the end of this paragraph
            previous_section = para[-200:]

    for idx, chunk in enumerate(chunks):
        chunk["index"] = idx

    logger.info(
        f"Chunking complete. Created {len(chunks)} chunks for {note_name}",
    )
    return chunks


if __name__ in "__main__":
    logger.info("Running chunker in standalone mode")
    chunks = chunker(note_name="./src/rag/test.txt")
    for chunk in chunks:
        print(chunk["content"])

    embeddings = embedder([chunk["content"] for chunk in chunks])
    for embedding in embeddings:
        print(embedding[:50])
