---
id: infra.backup-verify
name: Backup verification
description: Verify that scheduled backups exist, are recent, and are restorable.
domain: infrastructure
risk_level: low
owner: ops
---

# Backup verification

## Purpose

Confirm that JOL infrastructure backups are present, fresh, and actually
restorable. A backup that has never been restored is a hope, not a backup.

## When to run

- Daily, as part of `operations/morning-report.md`.
- On demand: "verify backups" / "backup status".
- Immediately after any storage migration or provider change.

## Steps

1. List backup artefacts for each registered system (object storage listing
   or backup tool inventory).
2. Check freshness: latest backup per system must be younger than its
   declared RPO. Flag anything older.
3. Integrity: verify checksums/signatures where available.
4. Restore drill (weekly or on demand): restore the latest backup of one
   randomly chosen system into a scratch location and validate contents.
5. Summarise: systems OK, systems stale, restore drill result.

## Constraints

- Read-only against production systems; restore drills run in scratch space
  only.
- Never log or report backup credentials or paths containing secrets.
- On failure: escalate via `incident-triage.md`, severity per missing-system
  criticality.

## Output

Markdown table: `system | last backup age | integrity | action required`,
followed by a one-line verdict (`OK` / `STALE` / `FAILED`).
