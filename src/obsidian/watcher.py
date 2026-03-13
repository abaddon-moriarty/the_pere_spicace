import sys
import logging
import threading


from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from src.config import settings
from src.rag.store import VaultStore
from src.rag.chunker import chunker
from src.rag.embedder import embedder
from src.obsidian.vault_structure import extract_metadata

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class VaultHandler(FileSystemEventHandler):
    def __init__(self, store):
        self.store = store
        self._timers = {}

    def _process_file(self, filepath):
        """Re-index the file after debounce delay."""
        logger.info(f"Re-indexing {filepath}")
        try:
            chunks = chunker(note_name=filepath)
            if not chunks:
                logger.debug(f"No chunks generated for {filepath}")
                return

            embeddings = embedder([chunk["content"] for chunk in chunks])
            if not embeddings:
                logger.warning(f"No embeddings returned for {filepath}")
                return

            metadata = extract_metadata(filepath)
            if not metadata:
                logger.warning(f"No metadata returned for {filepath}")
                return

            self.store.index_file(filepath, chunks, embeddings, metadata)
        except Exception:
            logger.exception(f"Failed to re-index {filepath}")

    def on_created(self, event):
        if not self.event_filter(event):
            return
        self.debounce(filepath=event.src_path)
        logger.info(f"File created: {event.src_path}")

    def on_modified(self, event):
        if not self.event_filter(event):
            return
        self.debounce(filepath=event.src_path)
        logger.info(f"File modified: {event.src_path}")

    def on_deleted(self, event):
        if not self.event_filter(event):
            return
        logger.info(f"File deleted: {event.src_path}")
        self.store.delete_file(event.src_path)

    def event_filter(self, event):
        if event.is_directory:
            return False
        return event.src_path.endswith(".md")

    def debounce(self, filepath):
        if filepath in self._timers:
            self._timers[filepath].cancel()
        # Start new timer
        timer = threading.Timer(5.0, self._process_file, args=[filepath])
        timer.daemon = True
        timer.start()
        self._timers[filepath] = timer


if __name__ == "__main__":
    path = settings.obsidian_vault_path

    if path is None:
        logger.warning(
            "OBSIDIAN_VAULT_PATH not set: vault indexing disabled.",
        )
        sys.exit(1)

    vault_path = Path(path)
    if not vault_path.exists():
        logger.error(f"Vault path does not exist: {vault_path}")

    store = VaultStore(persist_path="./chroma_db")
    handler = VaultHandler(store)

    observer = Observer()

    observer.schedule(handler, str(vault_path), recursive=True)

    logger.info(f"Watching vault at {vault_path}...")

    observer.start()
    try:
        while observer.is_alive():
            observer.join(1)  # wait with timeout to allow KeyboardInterrupt
    except KeyboardInterrupt:
        logger.info("Stopping watcher...")
    finally:
        observer.stop()
        observer.join()
