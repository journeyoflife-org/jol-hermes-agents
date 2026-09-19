"""Hermes agent bootstrap and repository validator.

Config-first design: this module loads and validates the declarative
artefacts (config/, skills/, memory/) without executing agent behaviour.
Runtime orchestration lives elsewhere; this is the single entry point for
CI and local checks.

Usage:
    python main.py validate   # validate config, skills and memory schema
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


def _resolve_root() -> Path:
    """Repo root = the directory containing config/hermes.yaml.

    Prefer the module's own directory (in-repo runs, CI); fall back to the
    current working directory when the module is imported from an installed
    location (e.g. the container entrypoint with artefacts in /app).
    """
    module_root = Path(__file__).resolve().parent
    if (module_root / "config" / "hermes.yaml").is_file():
        return module_root
    return Path.cwd()


ROOT = _resolve_root()

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

# ${ENV_VAR} references in config/ must be resolvable from the committed
# template; otherwise deployments fail open or with undefined semantics.
ENV_REF_PATTERN = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")
EXAMPLE_ENV_PATH = ROOT / "config" / "example.env"

# Mandate: every routed model must offer at least a 64k token context window
# and must be pinned to a stable, versioned identifier (never *-latest).
MIN_CONTEXT_LENGTH = 64_000


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
    lines = text.splitlines()
    # The closing fence is the first line after the opener that is exactly
    # '---'; substring splitting would break on bodies containing '---'.
    closing = next(
        (i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing is None:
        raise ValueError(f"{path}: unterminated YAML frontmatter")
    data = yaml.safe_load("\n".join(lines[1:closing]))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: frontmatter must be a mapping")
    return data


def check_required_files(paths: list[Path], kind: str) -> list[str]:
    errors: list[str] = []
    for path in paths:
        if not path.is_file():
            errors.append(f"missing {kind} file: {path.relative_to(ROOT)}")
            continue
        try:
            load_yaml(path)
        except (yaml.YAMLError, ValueError) as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    return errors


def check_provider_models(routing: dict) -> list[str]:
    """Enforce pinned model identifiers and a >=64k context window."""
    errors: list[str] = []
    for provider in routing.get("providers", []):
        name = provider.get("name")
        model = str(provider.get("model", ""))
        if model == "latest" or model.endswith("-latest"):
            errors.append(
                f"model-routing.yaml: provider '{name}' model '{model}' is an "
                f"unpinned mutable alias; pin a versioned model identifier"
            )
        context = provider.get("context_length")
        if not isinstance(context, int) or context < MIN_CONTEXT_LENGTH:
            errors.append(
                f"model-routing.yaml: provider '{name}' must declare an integer "
                f"context_length >= {MIN_CONTEXT_LENGTH}"
            )
    return errors


def validate_config() -> list[str]:
    errors = check_required_files(REQUIRED_CONFIG_FILES, "config")

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
        errors.extend(check_provider_models(routing))
    return errors


def _collect_env_key_values(node, refs: set[str]) -> None:
    """Collect values of keys using the '<name>_env' convention, e.g.
    api_key_env: HERMES_PRIMARY_API_KEY."""
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str) and key.endswith("_env") and isinstance(value, str):
                refs.add(value.strip())
            else:
                _collect_env_key_values(value, refs)
    elif isinstance(node, list):
        for item in node:
            _collect_env_key_values(item, refs)


def env_var_references(config_dir: Path) -> set[str]:
    refs: set[str] = set()
    for path in sorted(config_dir.rglob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        # Ignore comments so documentation examples ("${ENV_VAR}") are not
        # treated as live references.
        stripped = "\n".join(
            re.split(r"(?:^|\s)#", line, maxsplit=1)[0]
            for line in text.splitlines()
        )
        refs.update(ENV_REF_PATTERN.findall(stripped))
        # Bare env-var names via the *_env key convention.
        _collect_env_key_values(yaml.safe_load(text), refs)
    return {r for r in refs if ENV_REF_PATTERN.fullmatch(f"${{{r}}}")}


def example_env_keys(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, _ = line.partition("=")
        if sep:
            keys.add(key.strip())
    return keys


def validate_env_contract() -> list[str]:
    """Every env var referenced in config/ must exist in config/example.env."""
    errors: list[str] = []
    if not EXAMPLE_ENV_PATH.is_file():
        return [f"missing env template: {EXAMPLE_ENV_PATH}"]
    try:
        env_label = EXAMPLE_ENV_PATH.relative_to(ROOT)
    except ValueError:
        env_label = EXAMPLE_ENV_PATH
    referenced = env_var_references(ROOT / "config")
    declared = example_env_keys(EXAMPLE_ENV_PATH)
    for var in sorted(referenced - declared):
        errors.append(
            f"env contract: {var} referenced in config/ but absent from {env_label}"
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
    errors = check_required_files(REQUIRED_MEMORY_FILES, "memory")

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
    errors = (
        validate_config()
        + validate_skills()
        + validate_memory()
        + validate_env_contract()
    )
    if errors:
        for err in errors:
            print(f"FAIL  {err}", file=sys.stderr)
        print(f"\n{len(errors)} validation error(s)", file=sys.stderr)
        return 1
    print("OK    config, skills and memory schema are valid")
    return 0


def main(argv: list[str] = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "validate":
        return validate()
    print((__doc__ or "").strip())
    return 2 if args else 0


if __name__ == "__main__":
    raise SystemExit(main())
