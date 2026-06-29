"""Extraction unit tests (txt/md; PDF/DOCX paths use lazy parsers)."""

from __future__ import annotations

import pytest

from doc007.core.exceptions import ValidationError
from doc007.rag.extraction import extract


def test_extract_txt() -> None:
    pages = extract(b"Hello world.\nSecond line.", mime_type="text/plain", filename="a.txt")
    assert len(pages) == 1
    assert pages[0].number is None
    assert "Hello world" in pages[0].text


def test_extract_md() -> None:
    pages = extract(b"# Title\n\nBody text here.", mime_type="text/markdown", filename="a.md")
    assert "Title" in pages[0].text


def test_extract_rejects_unsupported() -> None:
    with pytest.raises(ValidationError):
        extract(b"\x89PNG", mime_type="image/png", filename="a.png")
