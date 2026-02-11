"""Tests for the RAG pipeline (unit tests that don't require a database or API)."""

from app.core.rag import split_into_chunks


class TestSplitIntoChunks:
    def test_splits_paragraphs(self):
        content = """First paragraph with more than enough text to be included in the results.

Second paragraph that also has enough content to easily pass the length filter.

Third paragraph for good measure and to test that multiple splits work correctly."""
        chunks = split_into_chunks(content, "test.md")
        assert len(chunks) == 3
        assert all(c["source"] == "test.md" for c in chunks)

    def test_skips_short_fragments(self):
        content = """A real paragraph with more than enough text to be included in results.

Hi

Another real paragraph that has sufficient content to pass the threshold here."""
        chunks = split_into_chunks(content, "test.md")
        assert len(chunks) == 2  # "Hi" is too short

    def test_empty_content(self):
        chunks = split_into_chunks("", "test.md")
        assert len(chunks) == 0

    def test_single_paragraph(self):
        content = "This is a single paragraph that should be long enough to be kept as a chunk."
        chunks = split_into_chunks(content, "test.md")
        assert len(chunks) == 1
