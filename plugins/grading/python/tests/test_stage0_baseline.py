"""Frozen regression baseline from a real marker_single run (see plan Task 14).

CI cannot run marker_single, so this asserts the committed baseline stays
well-formed and schema-valid — it guards against schema drift and accidental
corruption of the fixture.
"""

import re
from pathlib import Path

import yaml

from plugins.grading.python.schema import SourceMeta

BASELINE = Path(__file__).resolve().parent / "fixtures" / "stage0_baseline"
_IMG_LINK_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def test_baseline_content_md_nonempty():
    content = (BASELINE / "content.md").read_text(encoding="utf-8")
    assert content.strip(), "baseline content.md is empty"


def test_baseline_meta_validates():
    meta = yaml.safe_load((BASELINE / "meta.yaml").read_text(encoding="utf-8"))
    SourceMeta.model_validate(meta)
    assert meta["format"] == "pdf"
    assert meta["extraction"]["role"] == "marker_single"


def test_baseline_figure_links_resolve():
    content = (BASELINE / "content.md").read_text(encoding="utf-8")
    for target in _IMG_LINK_RE.findall(content):
        if "://" in target or target.startswith("/"):
            continue
        assert (BASELINE / target).is_file(), f"missing figure: {target}"
