"""Text extraction per file format.

Returns a list of `Page` objects. For PDFs each page is preserved with its
page number (1-based) so citations can reference the right page. For TXT and
MD the whole file is a single page with `number=None`.

Heavy parsers are imported lazily so importing this module is cheap and does
not require every parser to be installed.
"""

from __future__ import annotations

from dataclasses import dataclass

from doc007.core.exceptions import ValidationError


@dataclass
class Page:
    number: int | None
    text: str


def extract(data: bytes, *, mime_type: str, filename: str) -> list[Page]:
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

    if mime_type == "application/pdf" or ext == ".pdf":
        return _extract_pdf(data)
    if mime_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    } or ext == ".docx":
        return _extract_docx(data)
    if ext in {".md", ".markdown"} or mime_type == "text/markdown":
        return [Page(number=None, text=_decode(data))]
    if ext in {".txt", ""} or mime_type.startswith("text/"):
        return [Page(number=None, text=_decode(data))]

    raise ValidationError(f"Unsupported file type: {mime_type or ext}")


def _decode(data: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _extract_pdf(data: bytes) -> list[Page]:
    import io

    import pdfplumber

    pages: list[Page] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            pages.append(Page(number=i, text=page.extract_text() or ""))
    return pages


def _extract_docx(data: bytes) -> list[Page]:
    import io

    from docx import Document as DocxDocument

    doc = DocxDocument(io.BytesIO(data))
    text = "\n".join(p.text for p in doc.paragraphs)
    return [Page(number=None, text=text)]
