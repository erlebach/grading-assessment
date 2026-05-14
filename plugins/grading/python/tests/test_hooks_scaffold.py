import json
import os
import stat
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = PLUGIN_ROOT / "hooks"


def test_hooks_json_exists_and_parses():
    data = json.loads((HOOKS_DIR / "hooks.json").read_text())
    assert "hooks" in data
    assert isinstance(data["hooks"], dict)


def test_post_subagent_script_exists():
    p = HOOKS_DIR / "post_subagent_validate.sh"
    assert p.is_file()


def test_post_subagent_script_executable():
    p = HOOKS_DIR / "post_subagent_validate.sh"
    mode = p.stat().st_mode
    assert mode & stat.S_IXUSR, oct(mode)
