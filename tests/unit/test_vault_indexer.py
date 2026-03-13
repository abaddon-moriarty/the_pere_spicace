import json
import time


from unittest.mock import patch

import pytest

from src.obsidian.vault_indexer import index_vault, load_tracker, save_tracker

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_vault(tmp_path):
    """A minimal vault with two .md files and one file to skip."""
    note_a = tmp_path / "NoteA.md"
    note_a.write_text(
        "---\ntitle: Note A\n---\n# Section\
        \n\nSome content here that is long enough.",
        encoding="utf-8",
    )

    note_b = tmp_path / "NoteB.md"
    note_b.write_text(
        "---\ntitle: Note B\n---\n# Topic\
        \n\nAnother piece of content that is long enough.",
        encoding="utf-8",
    )

    templates_dir = tmp_path / "Templates"
    templates_dir.mkdir()
    template_note = templates_dir / "Template.md"
    template_note.write_text("# Template", encoding="utf-8")

    return tmp_path


@pytest.fixture
def tracker_file(tmp_path):
    """Returns a path for a tracker file inside tmp_path."""
    return tmp_path / ".vault_index_tracker.json"


# ---------------------------------------------------------------------------
# load_tracker / save_tracker
# ---------------------------------------------------------------------------


def test_load_tracker_missing_file(tmp_path):
    with patch(
        "src.obsidian.vault_indexer.TRACKER_FILE",
        tmp_path / "nonexistent.json",
    ):
        result = load_tracker()
    assert result == {}


def test_load_tracker_empty_file(tmp_path):
    f = tmp_path / "tracker.json"
    f.write_text("", encoding="utf-8")
    with patch("src.obsidian.vault_indexer.TRACKER_FILE", f):
        result = load_tracker()
    assert result == {}


def test_load_tracker_corrupt_file(tmp_path):
    f = tmp_path / "tracker.json"
    f.write_text("not valid json {{{", encoding="utf-8")
    with patch("src.obsidian.vault_indexer.TRACKER_FILE", f):
        result = load_tracker()
    assert result == {}


def test_load_tracker_valid_file(tmp_path):
    data = {"/some/path.md": 1700000000.0}
    f = tmp_path / "tracker.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with patch("src.obsidian.vault_indexer.TRACKER_FILE", f):
        result = load_tracker()
    assert result == data


def test_save_and_reload_tracker(tmp_path):
    f = tmp_path / "tracker.json"
    data = {"/a.md": 1700000001.5, "/b.md": 1700000002.5}
    with patch("src.obsidian.vault_indexer.TRACKER_FILE", f):
        save_tracker(data)
        result = load_tracker()
    assert result == data


# ---------------------------------------------------------------------------
# index_vault — environment / path guards
# ---------------------------------------------------------------------------


def test_index_vault_no_env(monkeypatch):
    """When vault path is None, index_vault returns early without raising."""
    monkeypatch.setattr("src.config.settings.obsidian_vault_path", None)
    index_vault()  # must not raise


def test_index_vault_nonexistent_path(monkeypatch, tmp_path):
    """When vault path does not exist, index_vault logs error and returns."""
    monkeypatch.setattr(
        "src.config.settings.obsidian_vault_path",
        tmp_path / "does_not_exist",
    )
    index_vault()  # must not raise


# ---------------------------------------------------------------------------
# index_vault — skipping logic
# ---------------------------------------------------------------------------


def test_index_vault_skips_already_indexed_files(
    monkeypatch,
    temp_vault,
    tmp_path,
):
    """Files whose mtime is older than last_indexed timestamp are skipped."""
    monkeypatch.setattr("src.config.settings.obsidian_vault_path", temp_vault)

    # Pre-populate tracker with a future timestamp so all files look indexed
    future_ts = time.time() + 9999
    tracker_data = {
        str(p): future_ts
        for p in temp_vault.rglob("*.md")
        if "Templates" not in str(p)
    }
    tracker_file = tmp_path / "tracker.json"
    tracker_file.write_text(json.dumps(tracker_data))

    with (
        patch("src.obsidian.vault_indexer.TRACKER_FILE", tracker_file),
        patch("src.obsidian.vault_indexer.VaultStore") as mock_store,
        patch("src.obsidian.vault_indexer.chunker") as mock_chunker,
    ):
        index_vault()
        mock_chunker.assert_not_called()
        mock_store.return_value.index_file.assert_not_called()


def test_index_vault_skips_templates_directory(
    monkeypatch,
    temp_vault,
    tmp_path,
):
    """Files inside a Templates/ directory are never indexed."""
    monkeypatch.setattr("src.config.settings.obsidian_vault_path", temp_vault)
    tracker_file = tmp_path / "tracker.json"
    tracker_file.write_text("{}")

    indexed_paths = []

    def fake_chunker(path):
        indexed_paths.append(path)
        return

    with (
        patch("src.obsidian.vault_indexer.TRACKER_FILE", tracker_file),
        patch("src.obsidian.vault_indexer.VaultStore"),
        patch("src.obsidian.vault_indexer.chunker", side_effect=fake_chunker),
    ):
        index_vault()

    assert not any("Templates" in p for p in indexed_paths)


# ---------------------------------------------------------------------------
# index_vault — force flag
# ---------------------------------------------------------------------------


def test_index_vault_force_reindexes_all(monkeypatch, temp_vault, tmp_path):
    """
    force=True re-indexes even files that appear up to date in the tracker.
    """
    monkeypatch.setattr("src.config.settings.obsidian_vault_path", temp_vault)

    future_ts = time.time() + 9999
    tracker_data = {
        str(p): future_ts
        for p in temp_vault.rglob("*.md")
        if "Templates" not in str(p)
    }
    tracker_file = tmp_path / "tracker.json"
    tracker_file.write_text(json.dumps(tracker_data))

    chunker_calls = []

    def fake_chunker(path):
        chunker_calls.append(path)
        return

    with (
        patch("src.obsidian.vault_indexer.TRACKER_FILE", tracker_file),
        patch("src.obsidian.vault_indexer.VaultStore"),
        patch("src.obsidian.vault_indexer.chunker", side_effect=fake_chunker),
    ):
        index_vault(force=True)

    assert len(chunker_calls) == 2  # NoteA + NoteB, no Templates


# ---------------------------------------------------------------------------
# index_vault — error resilience
# ---------------------------------------------------------------------------


def test_index_vault_chunker_exception_continues(
    monkeypatch,
    temp_vault,
    tmp_path,
):
    """A chunker exception on one file does not abort the rest."""
    monkeypatch.setattr("src.config.settings.obsidian_vault_path", temp_vault)
    tracker_file = tmp_path / "tracker.json"
    tracker_file.write_text("{}")

    call_count = {"n": 0}

    def flaky_chunker(_):
        call_count["n"] += 1
        if call_count["n"] == 1:
            msg = "disk error"
            raise RuntimeError(msg)
        return

    with (
        patch("src.obsidian.vault_indexer.TRACKER_FILE", tracker_file),
        patch("src.obsidian.vault_indexer.VaultStore"),
        patch("src.obsidian.vault_indexer.chunker", side_effect=flaky_chunker),
    ):
        index_vault()  # must not raise

    assert call_count["n"] == 2


def test_index_vault_embedding_exception_continues(
    monkeypatch,
    temp_vault,
    tmp_path,
):
    """An embedder exception on one file does not abort the rest."""
    monkeypatch.setattr("src.config.settings.obsidian_vault_path", temp_vault)
    tracker_file = tmp_path / "tracker.json"
    tracker_file.write_text("{}")

    fake_chunk = {
        "content": "text",
        "index": 0,
        "source": "x",
        "heading": "h",
    }

    embed_calls = {"n": 0}

    def flaky_embedder(_):
        embed_calls["n"] += 1
        if embed_calls["n"] == 1:
            msg = "VRAM OOM"
            raise RuntimeError(msg)
        return []

    with (
        patch("src.obsidian.vault_indexer.TRACKER_FILE", tracker_file),
        patch("src.obsidian.vault_indexer.VaultStore"),
        patch("src.obsidian.vault_indexer.chunker", return_value=[fake_chunk]),
        patch(
            "src.obsidian.vault_indexer.embedder",
            side_effect=flaky_embedder,
        ),
        patch(
            "src.obsidian.vault_indexer.extract_metadata",
            return_value={"title": ""},
        ),
    ):
        index_vault()

    assert embed_calls["n"] == 2


# ---------------------------------------------------------------------------
# index_vault — tracker update after success
# ---------------------------------------------------------------------------


def test_index_vault_updates_tracker_after_success(
    monkeypatch,
    temp_vault,
    tmp_path,
):
    """Tracker is written with a new timestamp after a successful index."""
    monkeypatch.setattr("src.config.settings.obsidian_vault_path", temp_vault)
    tracker_file = tmp_path / "tracker.json"
    tracker_file.write_text("{}")

    fake_chunk = {
        "content": "text",
        "index": 0,
        "source": "x",
        "heading": "h",
    }

    with (
        patch("src.obsidian.vault_indexer.TRACKER_FILE", tracker_file),
        patch("src.obsidian.vault_indexer.VaultStore"),
        patch("src.obsidian.vault_indexer.chunker", return_value=[fake_chunk]),
        patch(
            "src.obsidian.vault_indexer.embedder",
            return_value=[[0.1, 0.2]],
        ),
        patch(
            "src.obsidian.vault_indexer.extract_metadata",
            return_value={"title": ""},
        ),
    ):
        before = time.time()
        index_vault()
        after = time.time()

    saved = json.loads(tracker_file.read_text())
    assert len(saved) == 2
    for ts in saved.values():
        assert before <= ts <= after + 1
