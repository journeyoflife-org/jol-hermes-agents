#!/usr/bin/env python3
"""GDPR retention purge job (audit finding M5).

Executes memory/retention-policy.yaml mechanically against the sqlite
memory store:

- Store contract (memory/schema.yaml): one table per namespace, rows carry
  the common fields ``id`` and ``created_at`` (ISO-8601 UTC text).
- ``hard_delete`` namespaces: rows older than ``retention_days`` are deleted.
- ``anonymise`` namespaces: reported and SKIPPED — anonymisation needs
  personal-data column knowledge the policy does not declare; the runtime
  owns those transforms (flagged loudly so the gap stays visible).

Usage:
    python scripts/retention_purge.py [--db PATH] [--dry-run]

DB path resolution: --db > $HERMES_MEMORY_PATH > .env (python-dotenv).
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "memory" / "retention-policy.yaml"


def resolve_db_path(cli_value: str | None) -> Path:
    if cli_value:
        return Path(cli_value)
    load_dotenv(ROOT / ".env")
    from_env = os.environ.get("HERMES_MEMORY_PATH")
    if not from_env:
        raise SystemExit("retention_purge: HERMES_MEMORY_PATH is not set (see config/example.env)")
    return Path(from_env)


def load_rules() -> tuple[dict, dict]:
    with POLICY_PATH.open(encoding="utf-8") as fh:
        policy = yaml.safe_load(fh)
    default = policy.get("default", {})
    rules = {ns: {**default, **rule} for ns, rule in policy.get("retention", {}).items()}
    return rules, default


def purge_namespace(
    conn: sqlite3.Connection, namespace: str, rule: dict, now: datetime, dry_run: bool
) -> str:
    method = rule.get("purge_method", "hard_delete")
    if method == "anonymise":
        return "SKIPPED (anonymise is runtime-owned; see module docstring)"

    table = f'"{namespace}"'
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (namespace,)
    ).fetchone()
    if not exists:
        return "skipped (no such table)"

    days = int(rule.get("retention_days", 30))
    cutoff = (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    if dry_run:
        due = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE created_at < ?", (cutoff,)
        ).fetchone()[0]
        return f"dry-run: {due} row(s) due for hard_delete (cutoff {cutoff})"

    cur = conn.execute(f"DELETE FROM {table} WHERE created_at < ?", (cutoff,))
    return f"deleted {cur.rowcount} row(s) (cutoff {cutoff})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", help="sqlite store path (default: $HERMES_MEMORY_PATH)")
    parser.add_argument("--dry-run", action="store_true", help="report only, delete nothing")
    args = parser.parse_args(argv)

    db_path = resolve_db_path(args.db)
    if not db_path.is_file():
        raise SystemExit(f"retention_purge: memory store not found: {db_path}")

    rules, _ = load_rules()
    now = datetime.now(UTC)
    conn = sqlite3.connect(db_path)
    try:
        for namespace, rule in sorted(rules.items()):
            result = purge_namespace(conn, namespace, rule, now, args.dry_run)
            print(f"{namespace}: {result}")
        if not args.dry_run:
            conn.commit()
    finally:
        conn.close()

    print(f"retention_purge: {'dry-run ' if args.dry_run else ''}done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
