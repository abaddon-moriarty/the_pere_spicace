import re

import frontmatter


def chunker(note_name):
    chunks = []

    with open(note_name, encoding="utf-8") as file:
        post = frontmatter.load(file)
        body = post.content
        sections = re.split(r"(\#+.*)", body)
        chunks = []
        previous_section = ""

        for section in sections[:50]:
            if section:
                if len(section) > 2000:
                    section = section.split("\n\n")
                    # print("Large chunk detected")
                    # print(section)
                if re.match(r"#+.*", section):
                    current_heading = section.strip()
                    # print(f"Curent heading: {current_heading}")
                elif section.strip() and len(section.strip()) > 50:
                    chunks.append(
                        {
                            "heading": current_heading,
                            "content": f"{previous_section}\n{section.strip()}",
                            "source": note_name,
                        },
                    )

            previous_section = section.strip()[-200:]
    return chunks


if __name__ in "__main__":
    chunks = chunker(note_name="./src/rag/test.txt")
