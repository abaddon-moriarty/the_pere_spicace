import chromadb


class VaultStore:
    def __init__(self, persist_path: str):
        """
        Creates or opens a persistent ChromaDB client.
        Always use PersistentClient, never in-memory.
        Also create or retrieve the collection here,
        with hnsw:space set to cosine —
        this matters for text similarity quality.
        """
        self.client = chromadb.PersistentClient(path=persist_path)
        self.collection = self.client.get_or_create_collection(
            name="vault",
            configuration={"hnsw": {"space": "cosine"}},
        )

    def index_file(
        self,
        _filepath: str,
        _chunks: list[dict],
        _embeddings: list[list[float]],
    ):
        """
        Before inserting, delete all existing chunks for this file
        (filter by the source metadata field).
        Then upsert the new chunks.
        This handles both new files and re-indexing modified files identically.
        """
        return

    def delete_file(self, _filepath: str) -> None:
        """Remove all chunks belonging to a deleted file."""

    def query(
        self,
        _query_embedding: list[float],
        _n_results: int,
    ) -> list[dict]:
        """
        Return the top N most similar chunks with text and source metadata.
        """
        return []
