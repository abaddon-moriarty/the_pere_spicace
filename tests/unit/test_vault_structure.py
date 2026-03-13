import pytest

from src.obsidian.vault_structure import note_filter, build_vault_map

# ── Shared fixture ───────────────────────────────────────────────────────────


@pytest.fixture
def temp_vault_dir(tmp_path):
    """
    Creates a minimal vault directory:
      note.md        — valid frontmatter + content
      sub/other.md   — minimal frontmatter
      Templates/     — should be ignored entirely
    """
    note = tmp_path / "note.md"
    note.write_text(
        "---\n"
        "title: Test Note\n"
        "tags:\n  - python\n  - testing\n"
        "last_enriched: '2023-01-01'\n"
        "domain: development\n"
        "sources: https://example.com\n"
        "---\n"
        "This is the content of the test note.",
    )

    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    other = sub_dir / "other.md"
    other.write_text("---\ntitle: Other Note\n---\nOther content.")

    templates_dir = tmp_path / "Templates"
    templates_dir.mkdir()
    template = templates_dir / "template.md"
    template.write_text("---\ntitle: Template\n---\nTemplate content.")

    return tmp_path


# ── Tests ────────────────────────────────────────────────────────────────────


def test_build_vault_map_success(temp_vault_dir, monkeypatch):
    """Test building vault map with a controlled temp vault."""
    monkeypatch.setattr(
        "src.config.settings.obsidian_vault_path",
        temp_vault_dir,
    )
    vault_map = build_vault_map()

    assert vault_map is not None
    assert len(vault_map) == 2  # note.md and sub/other.md — Templates ignored

    assert "note.md" in vault_map
    assert "sub/other.md" in vault_map

    note = vault_map["note.md"]
    assert note["title"] == "Test Note"
    assert note["tags"] == ["python", "testing"]
    assert note["last_enriched"] == "2023-01-01"
    assert note["domain"] == "development"
    assert note["sources"] == "https://example.com"
    assert note["summary"] == "This is the content of the test note."


def test_build_vault_map_no_env(monkeypatch):
    """
    When OBSIDIAN_VAULT_PATH is not set, os.walk(None) raises TypeError,
    caught by the outer except — returns None.
    """
    monkeypatch.setattr("src.config.settings.obsidian_vault_path", None)

    vault_map = build_vault_map()

    assert vault_map is None


def test_build_vault_map_invalid_path(monkeypatch):
    """
    When the vault path does not exist, os.walk silently yields nothing
    and the function returns an empty dict (not None).
    """
    from pathlib import Path

    monkeypatch.setattr(
        "src.config.settings.obsidian_vault_path",
        Path("/nonexistent/path"),
    )
    vault_map = build_vault_map()

    # os.walk on a missing path returns an empty iterator — no exception raised
    assert vault_map == {}


def test_note_filter_keeps_unrelated_notes(temp_vault_dir, monkeypatch):
    """Notes whose sources don't contain the URL pass through unchanged."""
    monkeypatch.setattr(
        "src.config.settings.obsidian_vault_path",
        temp_vault_dir,
    )

    vault_map = build_vault_map()
    original_count = len(vault_map)

    url = "https://not-in-any-note.com"

    result = note_filter(vault_map, url)

    assert len(result) == original_count


def test_build_vault_map_handles_bad_file(temp_vault_dir, monkeypatch, caplog):
    """A file that raises during parsing is skipped and the error is logged."""
    monkeypatch.setattr(
        "src.config.settings.obsidian_vault_path",
        temp_vault_dir,
    )

    bad_file = temp_vault_dir / "bad.md"
    bad_file.write_bytes(
        b"\xff\xfe",
    )  # invalid UTF-8 — raises UnicodeDecodeError on open

    import logging

    with caplog.at_level(logging.ERROR, logger="src.obsidian.vault_structure"):
        vault_map = build_vault_map()

    assert "bad.md" not in vault_map
    assert "Error processing" in caplog.text


def test_note_filter_removes_already_enriched(temp_vault_dir, monkeypatch):
    """Notes whose sources contain the URL are removed from the vault map."""
    monkeypatch.setattr(
        "src.config.settings.obsidian_vault_path",
        temp_vault_dir,
    )
    vault_map = build_vault_map()

    # note.md has sources: https://example.com in the fixture
    url = "https://example.com"

    result = note_filter(vault_map, url)

    assert "note.md" not in result
    assert "sub/other.md" in result  # no sources → kept
