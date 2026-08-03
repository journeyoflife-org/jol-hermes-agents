"""Unit tests for the validator in main.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import main  # noqa: E402


def test_validate_passes_on_the_current_repo():
    assert main.validate() == 0


def test_parse_frontmatter_rejects_missing_header(tmp_path: Path):
    bad = tmp_path / "no-frontmatter.md"
    bad.write_text("# just markdown\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing YAML frontmatter"):
        main.parse_frontmatter(bad)


def test_load_yaml_rejects_non_mapping(tmp_path: Path):
    bad = tmp_path / "list.yaml"
    bad.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must be a mapping"):
        main.load_yaml(bad)


def test_main_without_args_prints_usage(capsys):
    assert main.main([]) == 0
    assert "Usage" in capsys.readouterr().out
