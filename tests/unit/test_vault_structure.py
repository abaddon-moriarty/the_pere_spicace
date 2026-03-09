from unittest.mock import patch

import pytest

from src.obsidian.vault_structure import build_vault_map

# ── Shared fixture ────────────────────────────────────────────────────────────


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


# ── Tests ─────────────────────────────────────────────────────────────────────


@patch("src.obsidian.vault_structure.load_dotenv")
def test_build_vault_map_success(
    mock_load_dotenv,
    temp_vault_dir,
    monkeypatch,
):
    """Test building vault map with a controlled temp vault."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(temp_vault_dir))

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


@patch("src.obsidian.vault_structure.load_dotenv")
def test_build_vault_map_no_env(mock_load_dotenv, monkeypatch):
    """
    When OBSIDIAN_VAULT_PATH is not set, os.walk(None) raises TypeError,
    caught by the outer except — returns None.
    """
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)

    vault_map = build_vault_map()

    assert vault_map is None


@patch("src.obsidian.vault_structure.load_dotenv")
def test_build_vault_map_invalid_path(mock_load_dotenv, monkeypatch):
    """
    When the vault path does not exist, os.walk silently yields nothing
    and the function returns an empty dict (not None).
    """
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/nonexistent/path")

    vault_map = build_vault_map()

    # os.walk on a missing path returns an empty iterator — no exception raised
    assert vault_map == {}


@patch("src.obsidian.vault_structure.load_dotenv")
def test_build_vault_map_skips_templates(
    mock_load_dotenv,
    temp_vault_dir,
    monkeypatch,
):
    """Files inside a Templates directory must be excluded."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(temp_vault_dir))

    vault_map = build_vault_map()

    assert "Templates/template.md" not in vault_map


@patch("src.obsidian.vault_structure.load_dotenv")
def test_build_vault_map_handles_bad_file(
    mock_load_dotenv,
    temp_vault_dir,
    monkeypatch,
    caplog,
):
    """A file that raises during parsing is skipped and the error is logged."""
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(temp_vault_dir))

    bad_file = temp_vault_dir / "bad.md"
    bad_file.write_bytes(
        b"\xff\xfe"
    )  # invalid UTF-8 — raises UnicodeDecodeError on open

    import logging

    with caplog.at_level(logging.ERROR, logger="src.obsidian.vault_structure"):
        vault_map = build_vault_map()

    assert "bad.md" not in vault_map
    assert "Error processing" in caplog.text
