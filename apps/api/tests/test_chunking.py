"""Chunking unit tests."""

from __future__ import annotations

from doc007.rag.chunking import chunk_pages, count_tokens
from doc007.rag.extraction import Page


def test_chunks_respect_token_budget() -> None:
    text = " ".join(f"Sentence number {i} with a few words." for i in range(200))
    chunks = chunk_pages([Page(number=None, text=text)], chunk_tokens=50, overlap_tokens=10)

    assert len(chunks) > 1
    assert all(c.content for c in chunks)
    # emitted chunks stay within budget (a lone oversized sentence is the only exception)
    assert all(c.token_count <= 60 for c in chunks)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_chunks_keep_page_numbers() -> None:
    pages = [
        Page(number=1, text="Alpha sentence here. " * 60),
        Page(number=2, text="Beta sentence here. " * 60),
    ]
    chunks = chunk_pages(pages, chunk_tokens=40, overlap_tokens=5)

    assert any(c.page_number == 1 for c in chunks)
    assert any(c.page_number == 2 for c in chunks)
    assert [c.chunk_index for c in chunks] == sorted(c.chunk_index for c in chunks)


def test_count_tokens_positive() -> None:
    assert count_tokens("hello world") >= 1
    assert count_tokens("") >= 0
