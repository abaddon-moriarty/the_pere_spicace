import logging

import chromadb

from rag.chunker import chunker
from rag.embedder import embedder

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


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
        embeddings: list[list[float]],
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
        metadatas = [{"source": chunk["source"]} for chunk in chunks]

        logger.debug(f"Upserting {len(ids)} chunks into collection")
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
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
        query_embedding: list[float],
        n_results: int,
    ) -> list[dict]:
        """
        Return the top N most similar chunks with text and source metadata.
        """
        logger.info(f"Querying collection for top {n_results} results")
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        # results is a dict with keys:
        #   ids, distances, metadatas, documents, etc.
        # Convert to a list of dicts for easier consumption
        formatted = []
        for i in range(len(results["ids"][0])):
            formatted.append(
                {
                    "id": results["ids"][0][i],
                    "distance": results["distances"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                },
            )
        logger.info(f"Query returned {len(formatted)} results")
        return formatted


if __name__ == "__main__":
    logger.info("Running VaultStore in standalone mode")
    chunks = chunker(note_name="./src/rag/test.txt")
    embeddings = embedder([chunk["content"] for chunk in chunks])

    store = VaultStore(persist_path="./chroma_db")
    store.index_file(
        filepath="./src/rag/test.txt",
        chunks=chunks,
        embeddings=embeddings,
    )

    if embeddings:
        sample_query = embeddings[0]  # use first chunk's embedding as query
        results = store.query(query_embedding=sample_query, n_results=3)
        for res in results:
            logger.info(
                f"Result: {res['document'][:100]}... \
                (distance: {res['distance']})",
            )
