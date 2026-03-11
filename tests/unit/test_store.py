import shutil
import tempfile
import unittest


from unittest.mock import patch, MagicMock

from rag.store import VaultStore

# ── Mocked unit tests (fast, no real ChromaDB) ───────────────────────────────


@patch("src.rag.store.chromadb.PersistentClient")
def test_vault_store_init(mock_persistent_client):
    """VaultStore wires the client and collection correctly."""
    mock_client = MagicMock()
    mock_persistent_client.return_value = mock_client
    mock_collection = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection

    store = VaultStore(persist_path="/fake/path")

    mock_persistent_client.assert_called_once_with(path="/fake/path")
    mock_client.get_or_create_collection.assert_called_once_with(
        name="vault",
        configuration={"hnsw": {"space": "cosine"}},
    )
    assert store.collection == mock_collection


@patch("src.rag.store.chromadb.PersistentClient")
def test_index_file_placeholder(mock_persistent_client):
    """index_file exists and does not raise."""
    mock_persistent_client.return_value = MagicMock()
    store = VaultStore(persist_path="/fake")
    store.index_file("file.md", [], [])


@patch("src.rag.store.chromadb.PersistentClient")
def test_delete_file_placeholder(mock_persistent_client):
    """delete_file exists and does not raise."""
    mock_persistent_client.return_value = MagicMock()
    store = VaultStore(persist_path="/fake")
    store.delete_file("file.md")


@patch("src.rag.store.chromadb.PersistentClient")
def test_query_placeholder(mock_persistent_client):
    """query exists and does not raise."""
    mock_persistent_client.return_value = MagicMock()
    store = VaultStore(persist_path="/fake")
    store.query([0.1, 0.2], 5)


# ── Integration tests (real ChromaDB on temp dir) ────────────────────────────


class TestVaultStoreIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.store = VaultStore(persist_path=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_creates_persistent_client(self):
        """VaultStore initialises with a real client and collection."""
        self.assertIsNotNone(self.store.client)
        self.assertIsNotNone(self.store.collection)

    def test_index_file_upserts_chunks(self):
        """index_file stores chunks retrievable via collection.get()."""
        chunks = [
            {"index": 0, "content": "chunk 1", "source": "test.txt"},
            {"index": 1, "content": "chunk 2", "source": "test.txt"},
        ]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]

        self.store.index_file("test.txt", chunks, embeddings)

        results = self.store.collection.get()
        self.assertGreater(len(results["ids"]), 0)

    def test_index_file_is_idempotent(self):
        """
        Calling index_file twice on the same file does not duplicate chunks.
        """
        chunks = [{"index": 0, "content": "chunk 1", "source": "test.txt"}]
        embeddings = [[0.1, 0.2]]

        self.store.index_file("test.txt", chunks, embeddings)
        self.store.index_file("test.txt", chunks, embeddings)

        results = self.store.collection.get(where={"source": "test.txt"})
        self.assertEqual(len(results["ids"]), 1)

    def test_delete_file_removes_chunks(self):
        """delete_file removes all chunks for the given source."""
        chunks = [{"index": 0, "content": "chunk 1", "source": "test.txt"}]
        embeddings = [[0.1, 0.2]]

        self.store.index_file("test.txt", chunks, embeddings)
        self.store.delete_file("test.txt")

        results = self.store.collection.get(where={"source": "test.txt"})
        self.assertEqual(len(results["ids"]), 0)

    def test_query_returns_formatted_results(self):
        """query returns dicts with the expected keys."""
        chunks = [
            {"index": 0, "content": "test content", "source": "test.txt"},
        ]
        embeddings = [[0.1, 0.2]]

        self.store.index_file("test.txt", chunks, embeddings)
        results = self.store.query(query_embedding=[0.1, 0.2], n_results=1)

        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertIn("id", results[0])
        self.assertIn("distance", results[0])
        self.assertIn("document", results[0])
        self.assertIn("metadata", results[0])

    def test_query_respects_n_results(self):
        """query returns at most n_results entries."""
        chunks = [
            {"index": i, "content": f"chunk {i}", "source": "test.txt"}
            for i in range(5)
        ]
        embeddings = [[0.1 * (i + 1), 0.2 * (i + 1)] for i in range(5)]

        self.store.index_file("test.txt", chunks, embeddings)
        results = self.store.query(query_embedding=[0.1, 0.2], n_results=3)

        self.assertLessEqual(len(results), 3)

    def test_metadata_source_is_stored(self):
        """Each indexed chunk has its source path in metadata."""
        chunks = [
            {"index": 0, "content": "some content", "source": "my_note.md"},
        ]
        embeddings = [[0.5, 0.5]]

        self.store.index_file("my_note.md", chunks, embeddings)
        results = self.store.collection.get(where={"source": "my_note.md"})

        self.assertEqual(len(results["ids"]), 1)
        self.assertEqual(results["metadatas"][0]["source"], "my_note.md")


if __name__ == "__main__":
    unittest.main()
