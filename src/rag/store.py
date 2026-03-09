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
        return


def delete_file(filepath: str):
    """
    removes all chunks belonging to a deleted file.
    """


def query(query_embedding: list[float], n_results: int) -> list[dict]:
    """
    returns the top N most similar chunks
    with their text and source metadata.
    """
