---
id: ops.morning-report
name: Morning report
description: Daily digest of infra health, backups, disk usage, and open Bitrix24 items.
domain: operations
risk_level: low
owner: ops
---

# Morning report

## Purpose

One consolidated, trustworthy digest each workday morning so the team
starts with the same picture of JOL's operational state.

## Schedule

- Workdays 07:30 (agent timezone, see `config/hermes.yaml`).
- On demand: "morning report" / "status".

## Composition

1. Run `infrastructure/backup-verify.md` — include its verdict line.
2. Disk usage on all managed hosts: flag filesystems ≥ 80 %, critical ≥ 90 %.
   (Deep cleanup is delegated to `operations/disk-cleanup.md`, never
   triggered automatically from this report.)
3. Overnight alerts summary: count by severity + one line each for SEV1/2.
4. Open Bitrix24 tasks assigned to the ops group (id, title, deadline).
5. Compliance status: result of the latest
   `infrastructure/compliance-scan.md` run (age of the run included).

## Constraints

- Read-only; the report never mutates anything.
- Keep total length under the gateway message limit; truncate with
  "… full report in memory namespace `ops.reports`".
- Personal data only as task assignee names; no customer data.

## Output

Single Markdown digest posted to the configured ops channel, and stored in
memory namespace `ops.reports` per retention policy.
