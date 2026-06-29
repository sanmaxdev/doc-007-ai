"""Token-aware, page-aware chunking.

Splits each page into sentence-ish segments, then greedily packs them into
chunks up to a token budget with a token overlap between consecutive chunks.
Each chunk keeps its page number and character offsets within the page so
citations can point back to the source.

Token counting uses tiktoken when available; if it cannot be loaded (e.g.
offline), it falls back to a character-based estimate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from doc007.core.config import settings
from doc007.rag.extraction import Page

_SENTENCE_RE = re.compile(r"\S.*?(?:[.!?]+(?=\s|$)|\n{2,}|$)", re.S)

_encoder = None
_encoder_loaded = False


@dataclass
class Chunk:
    content: str
    page_number: int | None
    char_start: int
    char_end: int
    token_count: int
    chunk_index: int = 0


def _get_encoder():
    global _encoder, _encoder_loaded
    if not _encoder_loaded:
        _encoder_loaded = True
        try:
            import tiktoken

            _encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:  # noqa: BLE001 - offline / not installed -> use fallback
            _encoder = None
    return _encoder


def count_tokens(text: str) -> int:
    enc = _get_encoder()
    if enc is not None:
        return len(enc.encode(text))
    return max(1, len(text) // 4)


def _segments(text: str) -> list[tuple[str, int, int]]:
    out: list[tuple[str, int, int]] = []
    for m in _SENTENCE_RE.finditer(text):
        raw = m.group()
        stripped = raw.strip()
        if not stripped:
            continue
        lead = len(raw) - len(raw.lstrip())
        start = m.start() + lead
        end = start + len(stripped)
        out.append((stripped, start, end))
    return out


def chunk_pages(
    pages: list[Page],
    *,
    chunk_tokens: int | None = None,
    overlap_tokens: int | None = None,
) -> list[Chunk]:
    budget = chunk_tokens or settings.chunk_size_tokens
    overlap = overlap_tokens or settings.chunk_overlap_tokens

    chunks: list[Chunk] = []
    index = 0

    def build(items: list[tuple[str, int, int, int]]) -> Chunk:
        nonlocal index
        content = " ".join(it[0] for it in items)
        chunk = Chunk(
            content=content,
            page_number=page.number,
            char_start=items[0][1],
            char_end=items[-1][2],
            token_count=sum(it[3] for it in items),
            chunk_index=index,
        )
        index += 1
        return chunk

    for page in pages:
        if not page.text or not page.text.strip():
            continue

        current: list[tuple[str, int, int, int]] = []
        current_tokens = 0

        for seg_text, start, end in _segments(page.text):
            tokens = count_tokens(seg_text)
            if current and current_tokens + tokens > budget:
                chunks.append(build(current))
                # carry a token-sized tail forward as overlap
                tail: list[tuple[str, int, int, int]] = []
                acc = 0
                for item in reversed(current):
                    tail.insert(0, item)
                    acc += item[3]
                    if acc >= overlap:
                        break
                current = tail
                current_tokens = sum(it[3] for it in current)
            current.append((seg_text, start, end, tokens))
            current_tokens += tokens

        if current:
            chunks.append(build(current))

    return chunks
