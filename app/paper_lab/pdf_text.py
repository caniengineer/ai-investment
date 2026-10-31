"""PDF -> text, page by page.

Uses ``pypdf`` (pure Python). Falls back to the ``pdftotext`` CLI (poppler) when
pypdf is missing or returns almost nothing, which happens with some SSRN PDFs.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("alphaagent.paper_lab.pdf")


@dataclass
class PaperText:
    pages: list[str]
    source: str

    @property
    def full_text(self) -> str:
        return "\n\n".join(f"[[page {i + 1}]]\n{p}" for i, p in enumerate(self.pages))

    @property
    def plain_text(self) -> str:
        return "\n\n".join(self.pages)


def _with_pypdf(path: Path) -> list[str]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return [(page.extract_text() or "") for page in reader.pages]


def _with_pdftotext(path: Path) -> list[str]:
    out = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"], check=True, capture_output=True, text=True
    ).stdout
    return out.split("\f")[:-1] if out.endswith("\f") else out.split("\f")


def extract_text(path: str | Path) -> PaperText:
    path = Path(path)
    if path.suffix.lower() in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8", errors="replace")
        pages = text.split("\f") if "\f" in text else [text]
        return PaperText(pages=pages, source=str(path))

    pages: list[str] = []
    try:
        pages = _with_pypdf(path)
    except Exception as e:  # pragma: no cover - depends on installed libs
        logger.warning("pypdf failed on %s: %s", path, e)

    if sum(len(p.strip()) for p in pages) < 200 and shutil.which("pdftotext"):
        try:
            pages = _with_pdftotext(path)
        except Exception as e:  # pragma: no cover
            logger.warning("pdftotext failed on %s: %s", path, e)

    if not pages:
        raise ValueError(f"Could not extract any text from {path}. Is it a scanned PDF? Run OCR first.")
    return PaperText(pages=pages, source=str(path))
