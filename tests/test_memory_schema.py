"""Memory schema enforcement: schema integrity and GDPR retention coverage."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "memory" / "schema.yaml"
POLICY_PATH = ROOT / "memory" / "retention-policy.yaml"

ALLOWED_TYPES = {"string", "integer", "datetime", "markdown", "boolean"}
ALLOWED_PURGE_METHODS = {"hard_delete", "anonymise"}


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def schema() -> dict:
    return load(SCHEMA_PATH)


@pytest.fixture(scope="module")
def policy() -> dict:
    return load(POLICY_PATH)


def test_schema_namespaces_are_unique_and_complete(schema: dict):
    namespaces = schema.get("namespaces", [])
    assert namespaces, "schema.yaml defines no namespaces"

    names = [ns["namespace"] for ns in namespaces]
    assert len(names) == len(set(names)), f"duplicate namespaces: {names}"

    for ns in namespaces:
        assert ns.get("description"), f"{ns['namespace']}: missing description"
        assert ns.get("fields"), f"{ns['namespace']}: defines no fields"
        for field in ns["fields"]:
            assert field.get("name"), f"{ns['namespace']}: field without name"
            assert field.get("type") in ALLOWED_TYPES, (
                f"{ns['namespace']}.{field['name']}: unknown type '{field.get('type')}'"
            )


def test_common_fields_present(schema: dict):
    common = schema.get("common_fields", [])
    names = {f["name"] for f in common}
    assert {"id", "created_at"} <= names, "common fields must include id and created_at"


def test_prohibited_content_classes(schema: dict):
    prohibited = schema.get("prohibited_content", [])
    assert "credentials" in prohibited
    assert "payment_data" in prohibited


def test_every_namespace_has_retention(schema: dict, policy: dict):
    """GDPR storage limitation: no namespace may exist without a purge rule."""
    schema_namespaces = {ns["namespace"] for ns in schema["namespaces"]}
    policy_namespaces = set(policy.get("retention", {}))
    uncovered = schema_namespaces - policy_namespaces
    assert not uncovered, f"namespaces without retention rules: {sorted(uncovered)}"


def test_retention_rules_are_mechanically_executable(policy: dict):
    for ns, rule in policy["retention"].items():
        assert isinstance(rule.get("retention_days"), int) and rule["retention_days"] > 0, (
            f"{ns}: retention_days must be a positive integer"
        )
        assert rule.get("purge_method") in ALLOWED_PURGE_METHODS, (
            f"{ns}: purge_method '{rule.get('purge_method')}' not in {ALLOWED_PURGE_METHODS}"
        )


def test_data_subject_rights_defined(policy: dict):
    rights = policy.get("data_subject_rights", {})
    erasure = rights.get("erasure", {})
    assert erasure.get("max_days"), "erasure deadline must be defined (GDPR Art. 17)"
    assert rights.get("access", {}).get("export_format"), (
        "access/export format must be defined (GDPR Art. 15)"
    )
