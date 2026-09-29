"""Tests for scripts/retention_purge.py and scripts/backup_memory.py (M5/M8)."""

from __future__ import annotations

import importlib.util
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


purge = load_script("retention_purge")
backup_mod = load_script("backup_memory")


@pytest.fixture()
def store(tmp_path: Path) -> Path:
    """A memory store per the schema.yaml contract: table per namespace."""
    db = tmp_path / "hermes-memory.sqlite"
    now = datetime.now(UTC)
    old = (now - timedelta(days=400)).strftime("%Y-%m-%dT%H:%M:%S")
    fresh = now.strftime("%Y-%m-%dT%H:%M:%S")
    conn = sqlite3.connect(db)
    # ops.reports: hard_delete, retention 90 days -> old row must go.
    conn.execute('CREATE TABLE "ops.reports" (id TEXT, created_at TEXT, digest TEXT)')
    conn.execute("INSERT INTO \"ops.reports\" VALUES ('r1', ?, 'old')", (old,))
    conn.execute("INSERT INTO \"ops.reports\" VALUES ('r2', ?, 'new')", (fresh,))
    # ops.incidents: anonymise -> purge must skip it entirely.
    conn.execute('CREATE TABLE "ops.incidents" (id TEXT, created_at TEXT, severity TEXT)')
    conn.execute("INSERT INTO \"ops.incidents\" VALUES ('i1', ?, 'SEV2')", (old,))
    conn.commit()
    conn.close()
    return db


def count(db: Path, table: str) -> int:
    conn = sqlite3.connect(db)
    try:
        return conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    finally:
        conn.close()


def test_purge_rules_cover_every_policy_namespace():
    rules, _ = purge.load_rules()
    assert {"ops.reports", "ops.incidents", "bitrix.tasks"} <= set(rules)
    assert rules["ops.reports"]["purge_method"] == "hard_delete"
    assert rules["ops.incidents"]["purge_method"] == "anonymise"


def test_purge_dry_run_changes_nothing(store: Path, capsys):
    assert purge.main(["--db", str(store), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "dry-run: 1 row(s) due" in out
    assert count(store, "ops.reports") == 2


def test_purge_hard_deletes_only_expired_rows(store: Path, capsys):
    assert purge.main(["--db", str(store)]) == 0
    out = capsys.readouterr().out
    assert count(store, "ops.reports") == 1  # old row purged, fresh kept
    assert count(store, "ops.incidents") == 1  # anonymise namespace untouched
    assert "SKIPPED (anonymise" in out


def test_purge_requires_db(tmp_path: Path):
    with pytest.raises(SystemExit, match="memory store not found"):
        purge.main(["--db", str(tmp_path / "missing.sqlite")])


def test_backup_creates_verifiable_copy(store: Path, tmp_path: Path, capsys):
    dest = tmp_path / "backups"
    assert backup_mod.main(["--db", str(store), "--dest", str(dest)]) == 0
    capsys.readouterr()
    copies = list(dest.glob("hermes-memory-*.sqlite"))
    assert len(copies) == 1
    assert count(copies[0], "ops.reports") == 2  # full snapshot, nothing purged


def test_backup_requires_existing_store(tmp_path: Path):
    with pytest.raises(SystemExit, match="memory store not found"):
        backup_mod.main(["--db", str(tmp_path / "missing.sqlite"), "--dest", str(tmp_path / "out")])
