import re


from pathlib import Path

import frontmatter


def chunker(note_name: str) -> list[dict]:
    """
    Split a markdown note into chunks based on headings.
    Each chunk includes the heading and the content under it
    until the next heading.
    Returns a list of dicts with keys: heading, content, source.
    """
    chunks = []
    with Path(note_name).open(encoding="utf-8") as file:
        post = frontmatter.load(file)
        body = post.content

    sections = re.split(r"(\#+.*)", body)
    previous_section = ""
    current_heading = ""

    for section in sections[:50]:
        if not section:
            continue

        # CASE 1: Section is a heading line (starts with #)
        if re.match(r"#+.*", section):
            current_heading = section.strip()
            previous_section = section.strip()[-200:]
            continue

        # CASE 2: Section is content
        # If content is too long, split into smaller paragraphs
        if len(section) > 2000:
            paragraphs = section.split("\n\n")
        else:
            paragraphs = [section]

        for para in paragraphs:
            para = para.strip()
            if not para or len(para) <= 50:
                continue

            chunks.append(
                {
                    "heading": current_heading,
                    "content": f"{previous_section}\n{para}",
                    "source": note_name,
                },
            )
            # Update previous_section with the end of this paragraph
            previous_section = para[-200:]

    return chunks


if __name__ in "__main__":
    chunks = chunker(note_name="./src/rag/test.txt")
