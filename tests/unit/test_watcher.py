import time
import threading


from unittest.mock import patch, MagicMock

import pytest


from watchdog.events import (
    DirModifiedEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
)

from src.obsidian.watcher import VaultHandler

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_store():
    return MagicMock()


@pytest.fixture
def handler(mock_store):
    return VaultHandler(store=mock_store)


# ---------------------------------------------------------------------------
# event_filter
# ---------------------------------------------------------------------------


def test_event_filter_accepts_md_file(handler):
    event = FileModifiedEvent("/vault/note.md")
    assert handler.event_filter(event) is True


def test_event_filter_rejects_non_md(handler):
    event = FileModifiedEvent("/vault/image.png")
    assert handler.event_filter(event) is False


def test_event_filter_rejects_directory(handler):
    event = DirModifiedEvent("/vault/subdir")
    assert handler.event_filter(event) is False


# ---------------------------------------------------------------------------
# on_deleted
# ---------------------------------------------------------------------------


def test_on_deleted_calls_delete_file(handler, mock_store):
    event = FileDeletedEvent("/vault/gone.md")
    handler.on_deleted(event)
    mock_store.delete_file.assert_called_once_with("/vault/gone.md")


def test_on_deleted_ignores_non_md(handler, mock_store):
    event = FileDeletedEvent("/vault/image.png")
    handler.on_deleted(event)
    mock_store.delete_file.assert_not_called()


# ---------------------------------------------------------------------------
# debounce
# ---------------------------------------------------------------------------


def test_debounce_fires_after_delay(handler):
    """_process_file is called once after the debounce timer expires."""
    called = threading.Event()

    with patch.object(
        handler,
        "_process_file",
        side_effect=lambda _: called.set(),
    ):
        handler.debounce("/vault/note.md")
        fired = called.wait(timeout=7)  # debounce is 5s

    assert fired


def test_debounce_cancels_previous_timer(handler):
    """Multiple rapid calls result in only one _process_file invocation."""
    call_count = {"n": 0}
    done = threading.Event()

    def fake_process(_):
        call_count["n"] += 1
        done.set()

    with patch.object(handler, "_process_file", side_effect=fake_process):
        for _ in range(5):
            handler.debounce("/vault/note.md")
            time.sleep(0.1)
        done.wait(timeout=8)

    assert call_count["n"] == 1


def test_debounce_independent_per_file(handler):
    """Each filepath gets its own debounce timer."""
    called_paths = []
    done = threading.Event()

    def fake_process(path):
        called_paths.append(path)
        if len(called_paths) == 2:
            done.set()

    with patch.object(handler, "_process_file", side_effect=fake_process):
        handler.debounce("/vault/a.md")
        handler.debounce("/vault/b.md")
        done.wait(timeout=8)

    assert set(called_paths) == {"/vault/a.md", "/vault/b.md"}


# ---------------------------------------------------------------------------
# on_created / on_modified trigger debounce
# ---------------------------------------------------------------------------


def test_on_created_triggers_debounce(handler):
    event = FileCreatedEvent("/vault/new.md")
    with patch.object(handler, "debounce") as mock_debounce:
        handler.on_created(event)
    mock_debounce.assert_called_once_with(filepath="/vault/new.md")


def test_on_modified_triggers_debounce(handler):
    event = FileModifiedEvent("/vault/existing.md")
    with patch.object(handler, "debounce") as mock_debounce:
        handler.on_modified(event)
    mock_debounce.assert_called_once_with(filepath="/vault/existing.md")


def test_on_created_ignores_non_md(handler):
    event = FileCreatedEvent("/vault/data.csv")
    with patch.object(handler, "debounce") as mock_debounce:
        handler.on_created(event)
    mock_debounce.assert_not_called()


# ---------------------------------------------------------------------------
# _process_file
# ---------------------------------------------------------------------------


def test_process_file_indexes_successfully(handler, mock_store):
    fake_chunks = [
        {"content": "text", "index": 0, "source": "x", "heading": "h"},
    ]
    fake_embeddings = [[0.1, 0.2, 0.3]]
    fake_metadata = {"title": "My Note", "tags": []}

    with (
        patch("src.obsidian.watcher.chunker", return_value=fake_chunks),
        patch("src.obsidian.watcher.embedder", return_value=fake_embeddings),
        patch(
            "src.obsidian.watcher.extract_metadata",
            return_value=fake_metadata,
        ),
    ):
        handler._process_file("/vault/note.md")

    mock_store.index_file.assert_called_once_with(
        "/vault/note.md",
        fake_chunks,
        fake_embeddings,
        fake_metadata,
    )


def test_process_file_skips_when_no_chunks(handler, mock_store):
    with patch("src.obsidian.watcher.chunker", return_value=None):
        handler._process_file("/vault/empty.md")

    mock_store.index_file.assert_not_called()


def test_process_file_skips_when_no_embeddings(handler, mock_store):
    fake_chunks = [
        {"content": "text", "index": 0, "source": "x", "heading": "h"},
    ]

    with (
        patch("src.obsidian.watcher.chunker", return_value=fake_chunks),
        patch("src.obsidian.watcher.embedder", return_value=[]),
    ):
        handler._process_file("/vault/note.md")

    mock_store.index_file.assert_not_called()


def test_process_file_handles_exception_gracefully(handler, mock_store):
    with patch(
        "src.obsidian.watcher.chunker",
        side_effect=RuntimeError("boom"),
    ):
        handler._process_file("/vault/note.md")

    mock_store.index_file.assert_not_called()
