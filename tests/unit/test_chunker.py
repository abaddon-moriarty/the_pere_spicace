import tempfile


from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import yaml
import pytest

from src.rag.chunker import chunker


class TestChunker:
    """Test suite for the chunker function."""

    @pytest.fixture
    def sample_markdown_file(self):
        """Create a temporary markdown file with frontmatter for testing."""
        content = """---
title: Test Note
---
# Section 1

This is a paragraph in section 1.It has more than 50 characters to be included.

## Subsection 1.1

Another paragraph with substantial content that should be chunked properly.

# Section 2

This is section 2 content. It's also long enough to be processed.
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(content)
            f.flush()
            yield f.name
        Path(f.name).unlink()

    @pytest.fixture
    def large_section_file(self):
        """Create a markdown file with a large section for testing."""
        content = (
            """---
title: Large Section Test
---
# Heading

"""
            + "\n\n".join([f"Paragraph {i}: " + "x" * 100 for i in range(30)])
            + "\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(content)
            f.flush()
            yield f.name
        Path(f.name).unlink()

    def test_chunker_returns_list_of_dicts(self, sample_markdown_file):
        """Test that chunker returns a list of dictionaries."""
        result = chunker(sample_markdown_file)
        assert isinstance(result, list)
        assert all(isinstance(chunk, dict) for chunk in result)

    def test_chunks_have_required_fields(self, sample_markdown_file):
        """Test that each chunk has all required fields."""
        chunks = chunker(sample_markdown_file)
        assert len(chunks) > 0, "Expected at least one chunk"
        required_fields = {"heading", "content", "source", "index"}
        for chunk in chunks:
            assert required_fields.issubset(chunk.keys())

    def test_chunks_have_sequential_indices(self, sample_markdown_file):
        """Test that chunk indices are sequential starting from 0."""
        chunks = chunker(sample_markdown_file)
        assert len(chunks) > 0, "Expected at least one chunk"
        indices = [int(chunk["index"]) for chunk in chunks]
        assert indices == list(range(len(chunks)))

    def test_source_field_matches_input(self, sample_markdown_file):
        """Test that source field contains the input file path."""
        chunks = chunker(sample_markdown_file)
        assert len(chunks) > 0, "Expected at least one chunk"
        for chunk in chunks:
            assert chunk["source"] == sample_markdown_file

    def test_heading_preserved_in_chunks(self, sample_markdown_file):
        """Test that headings are correctly associated with chunks."""
        chunks = chunker(sample_markdown_file)
        assert len(chunks) > 0, "Expected at least one chunk"
        assert chunks[0]["heading"] in [
            "# Section 1",
            "## Subsection 1.1",
            "# Section 2",
        ]

    def test_short_paragraphs_ignored(self, sample_markdown_file):
        """Test that paragraphs with 50 chars or fewer are ignored."""
        chunks = chunker(sample_markdown_file)
        assert len(chunks) > 0, "Expected at least one chunk"
        for chunk in chunks:
            assert len(chunk["content"]) > 50

    def test_large_section_split_into_paragraphs(self, large_section_file):
        """Test that sections larger than 2000 chars are split."""
        chunks = chunker(large_section_file)
        assert len(chunks) > 1

    def test_file_not_found_raises_error(self):
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            chunker("./nonexistent/file.md")

    def test_context_preserved_in_content(self, sample_markdown_file):
        """Test that previous section context is included in chunk content."""
        chunks = chunker(sample_markdown_file)
        if len(chunks) > 1:
            assert "\n" in chunks[1]["content"]

    @patch("rag.chunker.frontmatter.load")
    @patch("pathlib.Path.open", new_callable=mock_open, read_data="")
    def test_frontmatter_parse_error_handled(self, _mock_file, mock_load):
        mock_load.side_effect = yaml.YAMLError("Parser error")
        with pytest.raises(yaml.YAMLError):
            chunker("./test.md")

    def test_empty_sections_skipped(self, sample_markdown_file):
        """Test that empty sections are properly skipped."""
        chunks = chunker(sample_markdown_file)
        assert len(chunks) > 0, "Expected at least one chunk"
        assert all(chunk["content"].strip() for chunk in chunks)

    @patch(
        "pathlib.Path.open",
        new_callable=mock_open,
        read_data="No frontmatter, just text.",
    )
    def test_chunker_no_frontmatter(self, _):
        """Content under 50 chars with no headings produces no chunks."""
        with patch("rag.chunker.frontmatter.load") as mock_frontmatter:
            mock_post = MagicMock()
            mock_post.content = "Just plain text without headings."
            mock_frontmatter.return_value = mock_post

            chunks = chunker("fake.md")

            assert len(chunks) == 0
