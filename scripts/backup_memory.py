#!/usr/bin/env python3
"""Backup the sqlite memory store before risky operations (audit finding M8).

Mandate: snapshot state before first run and before Curator/GEPA-class
tooling. Uses the sqlite online backup API (safe against concurrent writers)
and verifies the copy with PRAGMA integrity_check.

Usage:
    python scripts/backup_memory.py [--db PATH] [--dest DIR]

Defaults: db = $HERMES_MEMORY_PATH (or .env), dest = runtime/backups.
Output: <dest>/hermes-memory-<UTC timestamp>.sqlite
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def resolve_db_path(cli_value: str | None) -> Path:
    if cli_value:
        return Path(cli_value)
    load_dotenv(ROOT / ".env")
    from_env = os.environ.get("HERMES_MEMORY_PATH")
    if not from_env:
        raise SystemExit("backup_memory: HERMES_MEMORY_PATH is not set (see config/example.env)")
    return Path(from_env)


def backup(db_path: Path, dest_dir: Path) -> Path:
    if not db_path.is_file():
        raise SystemExit(f"backup_memory: memory store not found: {db_path}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = dest_dir / f"hermes-memory-{stamp}.sqlite"

    source = sqlite3.connect(db_path)
    try:
        copy = sqlite3.connect(target)
        try:
            source.backup(copy)
        finally:
            copy.close()
    finally:
        source.close()

    check = sqlite3.connect(target)
    try:
        status = check.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        check.close()
    if status != "ok":
        target.unlink(missing_ok=True)
        raise SystemExit(f"backup_memory: integrity_check failed: {status}")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", help="sqlite store path (default: $HERMES_MEMORY_PATH)")
    parser.add_argument(
        "--dest", default=str(ROOT / "runtime" / "backups"), help="backup destination directory"
    )
    args = parser.parse_args(argv)

    target = backup(resolve_db_path(args.db), Path(args.dest))
    print(f"backup_memory: OK {target} ({target.stat().st_size} bytes, integrity ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
