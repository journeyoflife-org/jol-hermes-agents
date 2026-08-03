"""Hermes agent bootstrap and repository validator.

Config-first design: this module loads and validates the declarative
artefacts (config/, skills/, memory/) without executing agent behaviour.
Runtime orchestration lives elsewhere; this is the single entry point for
CI and local checks.

Usage:
    python main.py validate   # validate config, skills and memory schema
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent

REQUIRED_CONFIG_FILES = [
    ROOT / "config" / "hermes.yaml",
    ROOT / "config" / "model-routing.yaml",
    ROOT / "config" / "agent-policy.yaml",
    ROOT / "config" / "gateway" / "telegram.yaml",
]

REQUIRED_MEMORY_FILES = [
    ROOT / "memory" / "schema.yaml",
    ROOT / "memory" / "retention-policy.yaml",
]

SKILL_FRONTMATTER_FIELDS = {"id", "name", "description", "domain", "risk_level"}
ALLOWED_RISK_LEVELS = {"low", "medium", "high"}

# Regions considered acceptable for LLM providers (EU data residency).
ALLOWED_REGIONS = {"eu", "eu-central", "eu-west"}


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be a mapping")
    return data


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{path}: missing YAML frontmatter")
    _, raw, _ = text.split("---", 2)
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: frontmatter must be a mapping")
    return data


def validate_config() -> list[str]:
    errors: list[str] = []
    for path in REQUIRED_CONFIG_FILES:
        if not path.is_file():
            errors.append(f"missing config file: {path.relative_to(ROOT)}")
            continue
        try:
            load_yaml(path)
        except (yaml.YAMLError, ValueError) as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")

    routing_path = ROOT / "config" / "model-routing.yaml"
    if routing_path.is_file():
        routing = load_yaml(routing_path)
        for provider in routing.get("providers", []):
            region = str(provider.get("region", "")).lower()
            if region not in ALLOWED_REGIONS:
                errors.append(
                    f"model-routing.yaml: provider '{provider.get('name')}' "
                    f"region '{region}' is not EU-only"
                )
    return errors


def validate_skills() -> list[str]:
    errors: list[str] = []
    skills_root = ROOT / "skills"
    if not skills_root.is_dir():
        return ["missing skills/ directory"]
    for path in sorted(skills_root.rglob("*.md")):
        try:
            meta = parse_frontmatter(path)
        except (ValueError, yaml.YAMLError) as exc:
            errors.append(str(exc))
            continue
        missing = SKILL_FRONTMATTER_FIELDS - set(meta)
        if missing:
            errors.append(
                f"{path.relative_to(ROOT)}: frontmatter missing fields: {sorted(missing)}"
            )
        risk = meta.get("risk_level")
        if risk is not None and risk not in ALLOWED_RISK_LEVELS:
            errors.append(f"{path.relative_to(ROOT)}: invalid risk_level '{risk}'")
    return errors


def validate_memory() -> list[str]:
    errors: list[str] = []
    for path in REQUIRED_MEMORY_FILES:
        if not path.is_file():
            errors.append(f"missing memory file: {path.relative_to(ROOT)}")
            continue
        try:
            load_yaml(path)
        except (yaml.YAMLError, ValueError) as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")

    schema_path = ROOT / "memory" / "schema.yaml"
    policy_path = ROOT / "memory" / "retention-policy.yaml"
    if schema_path.is_file() and policy_path.is_file():
        schema = load_yaml(schema_path)
        policy = load_yaml(policy_path)
        schema_namespaces = {ns.get("namespace") for ns in schema.get("namespaces", [])}
        policy_namespaces = set(policy.get("retention", {}))
        uncovered = schema_namespaces - policy_namespaces
        if uncovered:
            errors.append(
                f"retention-policy.yaml: namespaces without retention rules: {sorted(uncovered)}"
            )
    return errors


def validate() -> int:
    errors = validate_config() + validate_skills() + validate_memory()
    if errors:
        for err in errors:
            print(f"FAIL  {err}", file=sys.stderr)
        print(f"\n{len(errors)} validation error(s)", file=sys.stderr)
        return 1
    print("OK    config, skills and memory schema are valid")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "validate":
        return validate()
    print(__doc__.strip())
    return 2 if args else 0


if __name__ == "__main__":
    raise SystemExit(main())
