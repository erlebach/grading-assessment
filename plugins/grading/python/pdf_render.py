"""PDF page rendering via pymupdf per spec §4.1.

One PNG per page, written to <out_dir>/page_NNN.png with 3-digit zero padding.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pymupdf


@dataclass(frozen=True)
class PageRenderResult:
    pdf_path: Path
    out_dir: Path
    page_count: int
    figure_paths: list[Path]


def render_pages(pdf_path: Path, out_dir: Path, *, dpi: int = 150) -> PageRenderResult:
    pdf_path = pdf_path.resolve()
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []
    with pymupdf.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=dpi)
            target = out_dir / f"page_{i:03d}.png"
            pix.save(target)
            paths.append(target)

    return PageRenderResult(
        pdf_path=pdf_path,
        out_dir=out_dir,
        page_count=len(paths),
        figure_paths=paths,
    )
