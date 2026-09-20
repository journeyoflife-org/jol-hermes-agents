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


# --- frontmatter parser robustness (audit finding M4) ---


def test_parse_frontmatter_tolerates_hr_in_body(tmp_path: Path):
    skill = tmp_path / "with-hr.md"
    skill.write_text(
        "---\nid: x.y\n---\n\nBody intro.\n\n---\n\nBody after a horizontal rule.\n",
        encoding="utf-8",
    )
    assert main.parse_frontmatter(skill) == {"id": "x.y"}


def test_parse_frontmatter_rejects_unterminated(tmp_path: Path):
    bad = tmp_path / "open-ended.md"
    bad.write_text("---\nid: x.y\nno closing fence\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unterminated YAML frontmatter"):
        main.parse_frontmatter(bad)


# --- model pinning & context window (audit finding H2) ---


def test_check_provider_models_rejects_latest_alias_and_short_context():
    routing = {
        "providers": [
            {"name": "p", "model": "mistral-large-latest", "context_length": 128000},
            {"name": "q", "model": "pinned-model-2411", "context_length": 8000},
            {"name": "r", "model": "pinned-model-2411"},
        ]
    }
    errors = main.check_provider_models(routing)
    assert any("'p'" in e and "unpinned" in e for e in errors)
    assert any("'q'" in e and "context_length" in e for e in errors)
    assert any("'r'" in e and "context_length" in e for e in errors)
    assert len(errors) == 3


def test_check_provider_models_accepts_pinned_large_context():
    routing = {
        "providers": [
            {"name": "p", "model": "mistral-large-2411", "context_length": 128000},
        ]
    }
    assert main.check_provider_models(routing) == []


def test_current_routing_is_pinned_with_sufficient_context():
    routing = main.load_yaml(main.ROOT / "config" / "model-routing.yaml")
    assert main.check_provider_models(routing) == []


# --- env-var contract (audit finding C2) ---


def test_env_var_references_and_env_keys(tmp_path: Path):
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "a.yaml").write_text(
        "# doc comment with ${NOT_A_REAL_REF}\n"
        "key: ${SOME_API_KEY}   # trailing ${ALSO_IGNORED}\n"
        "api_key_env: BARE_ENV_NAME\n"
        "other: plain\n",
        encoding="utf-8",
    )
    assert main.env_var_references(cfg) == {"SOME_API_KEY", "BARE_ENV_NAME"}

    env = tmp_path / "example.env"
    env.write_text("# comment\nSOME_API_KEY=\n\nnot_a_key_line\n", encoding="utf-8")
    assert main.example_env_keys(env) == {"SOME_API_KEY"}


def test_validate_env_contract_flags_missing_variable(tmp_path: Path, monkeypatch):
    sparse_env = tmp_path / "example.env"
    sparse_env.write_text("HERMES_MEMORY_PATH=\n", encoding="utf-8")
    monkeypatch.setattr(main, "EXAMPLE_ENV_PATH", sparse_env)
    errors = main.validate_env_contract()
    # The committed config references API keys the sparse template lacks.
    assert any("HERMES_PRIMARY_API_KEY" in e for e in errors)


def test_validate_env_contract_passes_on_the_current_repo():
    assert main.validate_env_contract() == []
