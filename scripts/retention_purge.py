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

Evidence contract (config/agent-policy.yaml ``control_definitions``): this job
is the ``scheduled_retention_purge`` deletion class — pre-approved by policy
under GDPR Art. 5(1)(e), so it needs no per-run human confirmation, but every
mutating run MUST append a row to ``audit.events``. The deletion and its
evidence commit in one transaction and the job **fails closed**: if the
``audit.events`` table is missing, everything is rolled back and nothing is
deleted. A deletion that outruns its own audit trail is a worse failure than a
purge that does not run.

Ad-hoc and data-subject-request deletions are NOT implemented here. Any future
implementation must honour the ``ad_hoc_or_dsr_deletion`` class: confirmation
plus a second factor, recorded in ``audit.approvals`` before execution.

Usage:
    python scripts/retention_purge.py [--db PATH] [--dry-run] [--run-id ID]

A dry run deletes nothing and writes no evidence row; its output is the
``dry_run_reviewed`` second-factor input for an ad-hoc deletion.

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

# Identity and authority for the evidence row. The scheduled purge has no
# human principal: the policy file is the authority, so autonomy_level uses
# the platform-job sentinel documented in memory/schema.yaml.
AUDIT_NAMESPACE = "audit.events"
DELETION_CLASS = "scheduled_retention_purge"
AGENT_ID = "agent:jol:hermes:retention:v1"
SKILL_ID = "retention.purge"
PRINCIPAL_REF = "scheduled-job"
TOOL = "sqlite.delete"
PLATFORM_JOB_LEVEL = -1


class AuditEvidenceError(RuntimeError):
    """A mutating run could not record its own evidence."""


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
) -> tuple[str, int]:
    """Return ``(human-readable outcome, rows actually deleted)``."""
    method = rule.get("purge_method", "hard_delete")
    if method == "anonymise":
        return "SKIPPED (anonymise is runtime-owned; see module docstring)", 0

    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (namespace,)
    ).fetchone()
    if not exists:
        return "skipped (no such table)", 0

    table = f'"{namespace}"'
    days = int(rule.get("retention_days", 30))
    cutoff = (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    if dry_run:
        due = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE created_at < ?", (cutoff,)
        ).fetchone()[0]
        return f"dry-run: {due} row(s) due for hard_delete (cutoff {cutoff})", 0

    cur = conn.execute(f"DELETE FROM {table} WHERE created_at < ?", (cutoff,))
    return f"deleted {cur.rowcount} row(s) (cutoff {cutoff})", cur.rowcount


def audit_table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (AUDIT_NAMESPACE,)
    ).fetchone()
    return row is not None


def record_audit_event(
    conn: sqlite3.Connection, run_id: str, counts: dict[str, int], now: datetime
) -> None:
    """Append one ``audit.events`` row inside the caller's transaction.

    Raises :class:`AuditEvidenceError` when the table is missing, so the caller
    rolls back and nothing is deleted.
    """
    if not audit_table_exists(conn):
        raise AuditEvidenceError(
            f"table '{AUDIT_NAMESPACE}' is missing from the memory store; the runtime "
            "must create one table per memory/schema.yaml namespace before this job "
            "may delete anything"
        )
    touched = "; ".join(f"{ns}:{n}" for ns, n in sorted(counts.items()) if n) or "none"
    conn.execute(
        f'INSERT INTO "{AUDIT_NAMESPACE}" ('
        "id, created_at, source_skill, run_id, principal_ref, agent_id, skill_id,"
        " autonomy_level, tools_invoked, data_classes_touched, result, error, evidence_ref)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            run_id,
            now.strftime("%Y-%m-%dT%H:%M:%S"),
            "scripts/retention_purge.py",
            run_id,
            PRINCIPAL_REF,
            AGENT_ID,
            SKILL_ID,
            PLATFORM_JOB_LEVEL,
            TOOL,
            touched,
            f"deleted {sum(counts.values())} row(s)",
            None,
            f"deletion_class:{DELETION_CLASS}",
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", help="sqlite store path (default: $HERMES_MEMORY_PATH)")
    parser.add_argument("--dry-run", action="store_true", help="report only, delete nothing")
    parser.add_argument(
        "--run-id", help="correlation id for the audit row (default: generated from UTC time)"
    )
    args = parser.parse_args(argv)

    db_path = resolve_db_path(args.db)
    if not db_path.is_file():
        raise SystemExit(f"retention_purge: memory store not found: {db_path}")

    rules, _ = load_rules()
    now = datetime.now(UTC)
    run_id = args.run_id or f"purge-{now.strftime('%Y%m%dT%H%M%SZ')}"

    outcomes: dict[str, str] = {}
    counts: dict[str, int] = {}
    conn = sqlite3.connect(db_path)
    try:
        for namespace, rule in sorted(rules.items()):
            outcomes[namespace], counts[namespace] = purge_namespace(
                conn, namespace, rule, now, args.dry_run
            )

        if args.dry_run:
            conn.rollback()  # a dry run writes nothing, not even evidence
            for namespace, message in outcomes.items():
                print(f"{namespace}: {message}")
            print(f"retention_purge: dry-run done (run_id {run_id})")
            print("  nothing deleted and no evidence row written; this output is the")
            print("  'dry_run_reviewed' second-factor input for an ad-hoc deletion.")
            return 0

        record_audit_event(conn, run_id, counts, now)
        conn.commit()
        for namespace, message in outcomes.items():
            print(f"{namespace}: {message}")
    except AuditEvidenceError as exc:
        conn.rollback()
        raise SystemExit(f"retention_purge: ABORTED, nothing deleted — {exc}") from exc
    finally:
        conn.close()

    print(f"retention_purge: done — deleted {sum(counts.values())} row(s)")
    print(f"  evidence: {AUDIT_NAMESPACE} run_id {run_id} deletion_class {DELETION_CLASS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
