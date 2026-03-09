from unittest.mock import patch, MagicMock

from src.rag.store import VaultStore


@patch("src.rag.store.chromadb.PersistentClient")
def test_vault_store_init(mock_persistent_client):
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
def test_index_file(mock_persistent_client):
    # Prevent real ChromaDB from being created
    mock_persistent_client.return_value = MagicMock()

    store = VaultStore(persist_path="/fake")
    # index_file is currently a placeholder — just verify it exists and doesn't raise
    store.index_file("file.md", [], [])


@patch("src.rag.store.chromadb.PersistentClient")
def test_delete_file(mock_persistent_client):
    mock_persistent_client.return_value = MagicMock()

    store = VaultStore(persist_path="/fake")
    # delete_file is currently a placeholder — just verify it exists and doesn't raise
    store.delete_file("file.md")


@patch("src.rag.store.chromadb.PersistentClient")
def test_query(mock_persistent_client):
    mock_persistent_client.return_value = MagicMock()

    store = VaultStore(persist_path="/fake")
    # query is currently a placeholder — just verify it exists and doesn't raise
    store.query([0.1, 0.2], 5)
