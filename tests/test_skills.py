"""Skill validation: every skill file is a well-formed contract."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"

REQUIRED_FIELDS = {"id", "name", "description", "domain", "risk_level"}
ALLOWED_RISK_LEVELS = {"low", "medium", "high"}
ALLOWED_DOMAINS = {"infrastructure", "operations", "bitrix"}

skill_files = sorted(SKILLS_DIR.rglob("*.md"))


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{path}: file must start with YAML frontmatter"
    _, raw, _ = text.split("---", 2)
    data = yaml.safe_load(raw)
    assert isinstance(data, dict), f"{path}: frontmatter must be a mapping"
    return data


def test_skills_directory_populated():
    assert skill_files, "no skill files found under skills/"


@pytest.mark.parametrize("path", skill_files, ids=lambda p: str(p.relative_to(ROOT)))
def test_skill_frontmatter_contract(path: Path):
    meta = parse_frontmatter(path)

    missing = REQUIRED_FIELDS - set(meta)
    assert not missing, f"missing frontmatter fields: {sorted(missing)}"

    assert meta["risk_level"] in ALLOWED_RISK_LEVELS, (
        f"risk_level '{meta['risk_level']}' not in {sorted(ALLOWED_RISK_LEVELS)}"
    )
    assert meta["domain"] in ALLOWED_DOMAINS, f"unknown domain '{meta['domain']}'"

    # Domain in frontmatter must match the directory the skill lives in.
    assert meta["domain"] == path.parent.name, (
        f"frontmatter domain '{meta['domain']}' != directory '{path.parent.name}'"
    )

    # id convention: <prefix>.<stem>, globally unique is checked below.
    assert "." in meta["id"], f"id '{meta['id']}' must use 'prefix.name' form"
    assert meta["id"].endswith(path.stem), f"id '{meta['id']}' should end with '{path.stem}'"

    assert str(meta["description"]).strip(), "description must not be empty"
    assert len(str(meta["description"])) <= 200, "description should stay one-liner sized"


def test_skill_ids_are_unique():
    ids = [parse_frontmatter(p)["id"] for p in skill_files]
    duplicates = {i for i in ids if ids.count(i) > 1}
    assert not duplicates, f"duplicate skill ids: {sorted(duplicates)}"


@pytest.mark.parametrize("path", skill_files, ids=lambda p: str(p.relative_to(ROOT)))
def test_skill_body_has_content(path: Path):
    text = path.read_text(encoding="utf-8")
    _, _, body = text.split("---", 2)
    assert body.strip(), f"{path}: skill body is empty"
    assert "## " in body, f"{path}: skill body must contain structured sections"
