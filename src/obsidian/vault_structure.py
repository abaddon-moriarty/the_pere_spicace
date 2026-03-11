import os
import logging


from pathlib import Path

import frontmatter


from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def build_vault_map() -> None | dict:
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
        if vault_path is None:
            logger.warning(
                "OBSIDIAN_VAULT_PATH not set - vault features disabled.",
            )
            return None
        logger.info("Building the Vault map.")

        vault_map = {}
        for root, _, files in os.walk(vault_path):
            for file in files:
                if (file.endswith(".md")) and ("Templates" not in root):
                    full_path = Path(root, file)
                    rel_path = str(full_path.relative_to(vault_path))
                    try:
                        with Path(full_path).open(encoding="utf-8") as f:
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
                    except Exception:
                        logger.exception(f"Error processing {full_path}")
                        continue

    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"OBSIDIAN_VAULT_PATH not set - vault features disabled.\n{e}",
        )
        return None

    logger.info(f"Found {len(vault_map)} markdown files.")
    return vault_map


def note_filter(vault_map: dict, url: str) -> dict:
    # Gets the vault map, the video url
    # removes any note that already contains the url as a source.
    # limits a tiny bit the length to process.
    keys_to_remove = []
    for name, metadata in vault_map.items():
        sources = metadata.get("sources")
        if sources is None:
            continue

        # Check if the URL is present in the sources
        found = False
        if isinstance(sources, list):
            for item in sources:
                if isinstance(item, str) and url in item:
                    found = True
                    break
        elif isinstance(sources, str) and url in sources:
            found = True

        if found:
            keys_to_remove.append(name)

    # Remove the identified entries
    for key in keys_to_remove:
        logger.info(
            f"Removing {key}. The video already contributed to it.",
        )
        del vault_map[key]

    return vault_map


def path_validation(vault_mapping):
    paths = vault_mapping["updates"]
    for note_path in paths:
        logger.debug(note_path)
        if not Path.exists(note_path):
            logger.error(f"{note_path} does not exist.")
    return


if __name__ == "__main__":
    logger.info(msg="Starting the vault map")
    load_dotenv()
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
    if vault_path:
        vault_data = build_vault_map()
        # Now you can use vault_data, e.g. print number of files
        if vault_data is not None:
            note_filter(
                vault_map=vault_data,
                url="https://www.youtube.com/watch?v=eDIj5LuIL4A&list=PLb49csYFtO2HAdNGChGzohFJGnJnXBOqd&index=2",
            )
    else:
        logger.warning("OBSIDIAN_VAULT_PATH not set.")
