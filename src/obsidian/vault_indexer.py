import os
import json
import logging
import argparse


from pathlib import Path
from datetime import datetime

from tqdm import tqdm
from dotenv import load_dotenv

from src.rag.store import VaultStore
from src.rag.chunker import chunker
from src.rag.embedder import embedder
from src.obsidian.vault_structure import extract_metadata

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

TRACKER_FILE = Path(".vault_index_tracker.json")


def load_tracker():
    if TRACKER_FILE.exists():
        try:
            with open(TRACKER_FILE) as f:
                content = f.read().strip()
                if not content:
                    logger.debug("Tracker file is empty, starting fresh.")
                    return {}
                return json.loads(content)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                f"Could not read tracker file: {e}. Starting fresh.",
            )
            return {}
    return {}


def save_tracker(tracker):
    with open(TRACKER_FILE, "w") as f:
        json.dump(tracker, f, indent=2)


def index_vault(force=False):
    load_dotenv()
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH")

    if vault_path is None:
        logger.warning(
            "OBSIDIAN_VAULT_PATH not set – vault indexing disabled.",
        )
        return
    vault_path = Path(vault_path)
    if not vault_path.exists():
        logger.error(f"Vault path does not exist: {vault_path}")
        return

    logger.info(f"Starting vault indexing from: {vault_path}")

    md_files = []
    for root, _, files in os.walk(vault_path):
        if "Templates" in root:
            continue
        for file in files:
            if file.endswith(".md"):
                full_path = Path(root) / file
                md_files.append(full_path)

    logger.info(f"Found {len(md_files)} markdown files to index.")

    # Load previous tracker
    tracker = load_tracker()
    logger.info(
        f"Loaded tracker with {len(tracker)} entries",
    )  # see if data is present
    store = VaultStore(persist_path="./chroma_db")

    files_to_index = []
    for file_path in md_files:
        current_mtime = file_path.stat().st_mtime
        key = str(file_path)
        last_indexed = tracker.get(
            key
        )  # float timestamp of when we last indexed
        if force or last_indexed is None or last_indexed < current_mtime:
            logger.debug(
                f"Will index: {key} | stored={last_indexed} | current={current_mtime}",
            )
            files_to_index.append(file_path)
        else:
            logger.debug(f"Skipping: {key} (indexed after last modification)")
    logger.info(f"Files to index (new/modified): {len(files_to_index)}")

    for file_path in tqdm(files_to_index, desc="Indexing vault", unit="file"):
        current_mtime = file_path.stat().st_mtime
        try:
            chunks = chunker(str(file_path))
        except Exception:
            logger.exception(f"Chunking failed for {file_path}")
            continue

        if not chunks:
            logger.warning(f"No chunks generated for {file_path}")
            # Still record as indexed?
            # Probably not, because there's nothing in DB.
            # We could skip updating mtime, so next run will try again.
            continue

        texts = [chunk["content"] for chunk in chunks]
        try:
            embeddings = embedder(texts)
        except Exception:
            logger.exception(f"Embedding failed for {file_path}")
            continue

        if not embeddings:
            logger.warning(f"No embeddings returned for {file_path}")
            continue

        logger.debug(f"Generated {len(embeddings)} embeddings")
        metadata = extract_metadata(file_path)
        if metadata is None:
            logger.warning(f"No metadata returned for {file_path}")
            continue

        store.index_file(
            filepath=str(file_path),
            chunks=chunks,
            embeddings=embeddings,
            file_metadata=metadata,
        )

        # Update tracker only after successful indexing
        tracker[str(file_path)] = datetime.now().timestamp()
        save_tracker(tracker)

    logger.info("Vault indexing complete.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-index all files",
    )
    args = parser.parse_args()
    index_vault(force=args.force)
