import re


from pathlib import Path

import frontmatter


def chunker(note_name: str):
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

    for section in sections[:50]:
        if section:
            if len(section) > 2000:
                section = section.split("\n\n")

            if re.match(r"#+.*", section):
                current_heading = section.strip()
            elif section.strip() and len(section.strip()) > 50:
                chunks.append(
                    {
                        "heading": current_heading,
                        "content": (f"{previous_section}\n{section.strip()}"),
                        "source": note_name,
                    },
                )

        previous_section = section.strip()[-200:]
    return chunks


if __name__ in "__main__":
    chunks = chunker(note_name="./src/rag/test.txt")
