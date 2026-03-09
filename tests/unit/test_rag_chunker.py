from unittest.mock import patch, MagicMock, mock_open

from src.rag.chunker import chunker


def test_chunker_with_markdown_file(tmp_path):
    # Content sections must be > 50 chars each or the chunker skips them
    md_content = """---
title: Test
---
# Heading 1
This is the content under heading 1.
It contains enough text to pass the minimum length threshold
set in the chunker.

## Heading 2
More content here under heading 2.
This section also needs to be long enough to exceed
the fifty character minimum.
"""
    file_path = tmp_path / "test.md"
    file_path.write_text(md_content)

    chunks = chunker(str(file_path))

    assert len(chunks) >= 2  # at least two sections
    # Check chunk structure
    for chunk in chunks:
        assert "heading" in chunk
        assert "content" in chunk
        assert "source" in chunk
        assert chunk["source"] == str(file_path)

    # Check first chunk (could be # Heading 1 + content)
    assert any("Heading 1" in c["heading"] for c in chunks)
    assert any("content under heading 1" in c["content"] for c in chunks)


@patch(
    "pathlib.Path.open",
    new_callable=mock_open,
    read_data="No frontmatter, just text.",
)
def test_chunker_no_frontmatter(_):
    # The open patch is needed to satisfy the decorator
    # mock_file receives the injected mock
    with patch("src.rag.chunker.frontmatter.load") as mock_frontmatter:
        mock_post = MagicMock()
        mock_post.content = "Just plain text without headings."
        mock_frontmatter.return_value = mock_post

        chunks = chunker("fake.md")

        # No headings → no chunks.
        # Content is also < 50 chars so would be skipped anyway.
        assert len(chunks) == 0
