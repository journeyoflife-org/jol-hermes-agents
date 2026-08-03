---
id: bitrix.task-create
name: Bitrix24 task creation
description: Create structured follow-up tasks in Bitrix24 from incidents, scans, or reports.
domain: bitrix
risk_level: medium
owner: ops
---

# Bitrix24 task creation

## Purpose

Turn agent findings (incidents, compliance findings, report action items)
into trackable Bitrix24 tasks with owner, deadline, and source traceability.

## When to run

- Called by `incident-triage.md` (SEV1/SEV2) and `compliance-scan.md`
  (high/critical findings).
- On demand: "create bitrix task …".

## Steps

1. Resolve credentials from env (`BITRIX24_BASE_URL`,
   `BITRIX24_WEBHOOK_TOKEN`); fail fast if unset.
2. Compose the task:
   - **Title**: `[<source-skill>] <one-line summary>`
   - **Description**: context, evidence summary, recommended next actions,
     link/reference to the originating run.
   - **Responsible**: mapped from the domain owner in the source skill's
     frontmatter; ask the user if unmapped — never guess a person.
   - **Deadline**: per severity (SEV1: +4h, SEV2: +1 business day,
     compliance: +3 business days) unless the caller specifies one.
3. Create the task via webhook; retry once on 5xx/timeout.
4. Post the task id + link back to the originating conversation.
5. Record metadata in memory namespace `bitrix.tasks`.

## Constraints

- Idempotency: before creating, check for an open task with the same title
  prefix from the same source run; comment on it instead of duplicating.
- Never create tasks on personal errands or outside ops/compliance domains.

## Output

`created | task id | url | assignee | deadline` or explicit failure reason.
