import json
import logging


from pathlib import Path
from collections.abc import Sequence

import chromadb

from src.rag.chunker import chunker
from src.rag.embedder import embedder
from src.obsidian.vault_structure import extract_metadata

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class VaultStore:
    def __init__(self, persist_path: str):
        """
        Creates or opens a persistent ChromaDB client.
        Always use PersistentClient, never in-memory.
        Also create or retrieve the collection here,
        with hnsw:space set to cosine —
        this matters for text similarity quality.
        """
        logger.info(
            f"Initializing VaultStore with persist_path: {persist_path}",
        )
        self.client = chromadb.PersistentClient(path=persist_path)
        self.collection = self.client.get_or_create_collection(
            name="vault",
            configuration={"hnsw": {"space": "cosine"}},
        )
        logger.info("Collection 'vault' ready (hnsw.space = cosine)")

    def index_file(
        self,
        filepath: str,
        chunks: list[dict],
        embeddings: Sequence[Sequence[float]],
        file_metadata: dict | None = None,
    ):
        """
        Before inserting, delete all existing chunks for this file
        (filter by the source metadata field).
        Then upsert the new chunks.
        This handles both new files and re-indexing modified files identically.
        """
        logger.info(f"Indexing file: {filepath} with {len(chunks)} chunks")
        # Delete existing chunks for this file
        self.delete_file(filepath)

        # Prepare data for upsert
        ids = [f"{filepath}_chunk_{chunk['index']}" for chunk in chunks]
        documents = [chunk["content"] for chunk in chunks]
        metadatas = []
        for chunk in chunks:
            # base metadata: source
            chunk_meta = {"source": chunk["source"]}
            # merge file-level metacouldata if provided
            if file_metadata:
                meta_copy = file_metadata.copy()
                for key, value in meta_copy.items():
                    if isinstance(value, list):
                        if all(isinstance(v, str) for v in value):
                            meta_copy[key] = ", ".join(
                                value,
                            )  # tags: ["a", "b"] → "a, b"
                        else:
                            meta_copy[key] = json.dumps(
                                value,
                            )
                    elif isinstance(value, dict):
                        meta_copy[key] = json.dumps(value)
                    elif value is None:
                        meta_copy[key] = ""
                chunk_meta.update(meta_copy)
            metadatas.append(chunk_meta)

        logger.debug(f"Upserting {len(ids)} chunks into collection")
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,  # type: ignore[arg-type]
            documents=documents,
            metadatas=metadatas,  # type: ignore[arg-type]
        )
        logger.info(f"Successfully indexed {filepath}")

    def delete_file(self, filepath: str) -> None:
        """Remove all chunks belonging to a deleted file."""
        logger.info(f"Deleting all chunks for file: {filepath}")
        # Use where filter to delete by source metadata
        self.collection.delete(where={"source": filepath})
        logger.info(f"Chunks from {filepath} deleted.")

    def query(
        self,
        query_embedding: Sequence[float],
        n_results: int,
    ) -> list[dict]:
        """
        Return the top N most similar chunks with text and source metadata.
        """
        logger.info(f"Querying collection for top {n_results} results")
        results = self.collection.query(
            query_embeddings=[query_embedding],  # type: ignore[arg-type]
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        # results is a dict with keys:
        #   ids, distances, metadatas, documents, etc.
        # Convert to a list of dicts for easier consumption
        formatted = []
        ids = results.get("ids") or [[]]
        distances = results.get("distances") or [[]]
        documents = results.get("documents") or [[]]
        metadatas = results.get("metadatas") or [[]]
        for i in range(len(ids[0])):
            formatted.append(
                {
                    "id": ids[0][i],
                    "distance": distances[0][i],
                    "document": documents[0][i],
                    "metadata": metadatas[0][i],
                },
            )
        logger.info(f"Query returned {len(formatted)} results")
        return formatted


if __name__ == "__main__":
    logger.info("Running VaultStore in standalone mode")
    url = "./Is RAG Still Needed? Choosing the Best Approach for LLMs.txt"

    file_path = Path(url)
    chunks = chunker(note_name=str(file_path))
    embeddings = []
    store = VaultStore(persist_path="./chroma_db")
    if chunks:
        embeddings = embedder([chunk["content"] for chunk in chunks])

        metadata = extract_metadata(file_path)
        logger.info(f"Extracted metadata from {file_path}: \n{metadata}")
        store.index_file(
            filepath="./src/rag/test.txt",
            chunks=chunks,
            embeddings=embeddings,
            file_metadata=metadata,
        )

    if embeddings:
        sample_query = embeddings[0]  # use first chunk's embedding as query
        results = store.query(query_embedding=sample_query, n_results=10)
        for res in results:
            logger.info(
                f"Source file: {res['metadata']}\
                \nResult: {res['document']}... \
                \n(distance: {res['distance']})",
            )
