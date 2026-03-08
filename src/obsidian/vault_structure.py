import os
import logging

import frontmatter


from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def build_vault_map():
    """
    Build a map of markdown files in an Obsidian vault with metadata.

    This function recursively walks through a vault directory, identifies
    all markdown files, extracts their frontmatter metadata and content,
    and creates a structured map of the vault.

    Args:
        vault_path (str): The root path to the Obsidian vault directory.

    Returns:
        dict: A dictionary mapping relative file paths to their metadata.
              Each entry contains:
              - "title" (str): The title from the file's frontmatter.
              - "tags" (list): Tags from the file's frontmatter.
              - "summary" (str): First 300 characters of the file's content.

    Note:
        Files that fail to process due to exceptions are skipped silently.
        Only files with .md extension are processed.
    """

    logger.info("Loading environment variables")

    try:
        load_dotenv()
        vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
        logger.info("Building the Vault map.")

        vault_map = {}
        for root, _, files in os.walk(vault_path):
            for file in files:
                if (file.endswith(".md")) and ("Templates" not in root):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, vault_path)

                    try:
                        with open(full_path, encoding="utf-8") as f:
                            post = frontmatter.load(f)
                            metadata = post.metadata
                            content = post.content

                        title = metadata.get("title", "")
                        tags = metadata.get("tags", [])
                        last_enriched = metadata.get("last_enriched", "")
                        sources = metadata.get("sources", "")
                        domain = metadata.get("domain", "")
                        summary = content[:300]

                        vault_map[rel_path] = {
                            "title": title,
                            "tags": tags,
                            "last_enriched": last_enriched,
                            "domain": domain,
                            "sources": sources,
                            "summary": summary,
                        }
                    except Exception as e:
                        logger.exception(f"Error processing {full_path}: {e}")
                        continue

    except Exception as e:
        logger.warning(
            f"OBSIDIAN_VAULT_PATH not set – vault features disabled. or\n {e}",
        )
        return None

    logger.info(f"Found {len(vault_map)} markdown files.")
    return vault_map


def note_filter(vault_map: dict, url: str) -> dict:
    # Gets the vault map, the video url and removes any note that already contains the url as a source.
    # limits a tiny bit the length to process.
    for name, metadata in vault_map.items():
        if (
            name
            == "Training/Computer Vision/OpenCV with Python — Comprehensive Technical Notes.md"
        ):
            for data in metadata.items():
                if data[0] == "sources":
                    print(data)


if __name__ == "__main__":
    load_dotenv()
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
    if vault_path:
        vault_data = build_vault_map()
        # Now you can use vault_data, e.g. print number of files
        logger.info(f"Found {len(vault_data)} markdown files.")

        note_filter(
            vault_map=vault_data,
            url="https://www.youtube.com/watch?v=eDIj5LuIL4A&list=PLb49csYFtO2HAdNGChGzohFJGnJnXBOqd&index=2",
        )
    else:
        logger.warning("OBSIDIAN_VAULT_PATH not set.")
