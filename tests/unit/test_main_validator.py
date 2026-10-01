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


# --- self-hosted mTLS provider schema (Phase 2) ---


def _self_hosted(**over):
    prov = {
        "name": "sh", "kind": "self-hosted", "model": "qwen3-32b-q8_0",
        "context_length": 32768, "base_url": "https://llm.jol.internal:8443/v1",
        "api_key_env": "K", "tls_client_cert_env": "C",
        "tls_client_key_env": "CK", "tls_ca_cert_env": "CA",
    }
    prov.update(over)
    return {"providers": [prov]}


def test_self_hosted_accepts_native_32k_context():
    # Native (no-YaRN) window passes the self-hosted floor; a SaaS provider of
    # the same size must still be rejected against the 64k floor.
    assert main.check_provider_models(_self_hosted()) == []
    saas = {"providers": [{"name": "p", "model": "x-2411", "context_length": 32768}]}
    assert any("64000" in e for e in main.check_provider_models(saas))


def test_self_hosted_below_native_floor_is_rejected():
    errors = main.check_provider_models(_self_hosted(context_length=31999))
    assert any("32000" in e for e in errors)


def test_unknown_kind_is_rejected():
    errors = main.check_provider_models(_self_hosted(kind="on-prem"))
    assert any("unknown kind" in e for e in errors)


def test_self_hosted_requires_https_base_url_and_all_transport_refs():
    routing = _self_hosted(base_url="http://llm.jol.internal:8443/v1")
    del routing["providers"][0]["tls_ca_cert_env"]
    errors = main.check_provider_transport(routing)
    assert any("https base_url" in e for e in errors)
    assert any("tls_ca_cert_env" in e for e in errors)


def test_saas_provider_is_exempt_from_transport_checks():
    saas = {"providers": [{"name": "p", "model": "x-2411", "context_length": 128000}]}
    assert main.check_provider_transport(saas) == []


def test_current_routing_declares_a_valid_self_hosted_provider():
    routing = main.load_yaml(main.ROOT / "config" / "model-routing.yaml")
    kinds = {pr.get("kind", "saas") for pr in routing["providers"]}
    assert "self-hosted" in kinds
    assert main.check_provider_transport(routing) == []


# --- data-class routing (Phase 3) ---


def _rt(chains, *, providers=None, blocked=("credentials", "payment_data"), default_chain=None):
    providers = providers if providers is not None else [
        {"name": "saas_p", "kind": "saas"},
        {"name": "sh", "kind": "self-hosted"},
    ]
    rb = {"chains": chains, "blocked_data_classes": list(blocked)}
    if default_chain is not None:
        rb["default_chain"] = default_chain
    return {"providers": providers, "routing": rb}


def test_routing_sensitive_must_be_self_hosted():
    ok = _rt([{"name": "sensitive", "data_classes": ["personal_data"], "providers": ["sh"]}])
    assert main.check_routing_policy(ok) == []
    bad = _rt([{"name": "sensitive", "data_classes": ["special_category"],
               "providers": ["saas_p"]}])
    errors = main.check_routing_policy(bad)
    assert any("fail-closed" in e for e in errors)


def test_routing_rejects_undeclared_provider_and_unknown_class():
    bad = _rt([{"name": "c", "data_classes": ["mystery_class"], "providers": ["ghost"]}])
    errors = main.check_routing_policy(bad)
    assert any("undeclared provider" in e for e in errors)
    assert any("unknown data class" in e for e in errors)


def test_routing_rejects_ambiguous_and_blocked_classes():
    amb = _rt([
        {"name": "a", "data_classes": ["operational_telemetry"], "providers": ["saas_p"]},
        {"name": "b", "data_classes": ["operational_telemetry"], "providers": ["sh"]},
    ])
    assert any("ambiguous" in e for e in main.check_routing_policy(amb))
    blocked = _rt([{"name": "x", "data_classes": ["credentials"], "providers": ["sh"]}])
    assert any("blocked data class" in e for e in main.check_routing_policy(blocked))


def test_routing_default_chain_must_exist():
    rt = _rt([{"name": "standard", "data_classes": ["operational_telemetry"],
              "providers": ["saas_p"]}], default_chain="nonexistent")
    assert any("not a declared chain" in e for e in main.check_routing_policy(rt))


def test_routing_legacy_failover_shape_is_exempt():
    # A routing block with no `chains` (legacy failover) yields no data-class errors.
    legacy = {"providers": [{"name": "p", "kind": "saas"}],
              "routing": {"strategy": "failover"}}
    assert main.check_routing_policy(legacy) == []


def test_current_routing_passes_data_class_policy():
    routing = main.load_yaml(main.ROOT / "config" / "model-routing.yaml")
    assert main.check_routing_policy(routing) == []
