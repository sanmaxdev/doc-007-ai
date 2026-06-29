"""RAG pipeline modules (clean separation).

Phase 2/3 fill these in:
- extraction.py    per-format text extraction (PDF page-aware, DOCX, MD/TXT)
- cleaning.py      normalize / strip boilerplate
- chunking.py      token-aware chunking with overlap + metadata
- embeddings.py    EmbeddingProvider impl (OpenAI)
- vector_store.py  Qdrant wrapper — ALWAYS workspace-filtered
- retrieval.py     top-k + metadata filters (+ rerank later)
- prompt.py        safe RAG prompt builder + injection guardrails
- answer.py        orchestration: retrieve -> prompt -> LLM -> citations
"""
