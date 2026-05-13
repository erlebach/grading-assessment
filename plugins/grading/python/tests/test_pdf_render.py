from pathlib import Path

import pymupdf
import pytest

from plugins.grading.python.pdf_render import render_pages, PageRenderResult


@pytest.fixture
def two_page_pdf(tmp_path):
    """Generate a tiny 2-page PDF via pymupdf so tests don't need a binary fixture."""
    doc = pymupdf.open()
    for i in range(2):
        page = doc.new_page(width=200, height=200)
        page.insert_text((20, 50), f"page {i + 1}")
    out = tmp_path / "tiny.pdf"
    doc.save(out)
    doc.close()
    return out


def test_render_pages_produces_one_png_per_page(tmp_path, two_page_pdf):
    out_dir = tmp_path / "figures"
    result = render_pages(two_page_pdf, out_dir)
    assert isinstance(result, PageRenderResult)
    assert result.page_count == 2
    assert (out_dir / "page_001.png").is_file()
    assert (out_dir / "page_002.png").is_file()
    assert result.figure_paths == [out_dir / "page_001.png", out_dir / "page_002.png"]


def test_render_pages_zero_pads_to_three_digits(tmp_path, two_page_pdf):
    out_dir = tmp_path / "figures"
    render_pages(two_page_pdf, out_dir)
    names = sorted(p.name for p in out_dir.iterdir())
    assert names == ["page_001.png", "page_002.png"]


def test_render_pages_makes_output_dir(tmp_path, two_page_pdf):
    out_dir = tmp_path / "deep" / "nested" / "figures"
    assert not out_dir.exists()
    render_pages(two_page_pdf, out_dir)
    assert out_dir.is_dir()
