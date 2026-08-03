---
id: ops.disk-cleanup
name: Disk cleanup
description: Identify reclaimable disk space and remove approved artefact classes with confirmation.
domain: operations
risk_level: high
owner: ops
---

# Disk cleanup

## Purpose

Reclaim disk space safely. This is a mutating, high-risk skill: nothing is
deleted without an explicit human confirmation of the concrete deletion plan.

## When to run

- When any managed filesystem ≥ 80 % (flagged by `morning-report.md`).
- On demand: "disk cleanup <host>".

## Steps

1. **Measure** — per-filesystem usage and top-20 largest directories.
2. **Classify** reclaimable candidates into approved classes only:
   - rotated/truncated application logs (older than retention window)
   - package manager caches
   - tmp/scratch files older than 7 days
   - old container images not referenced by any running container
3. **Plan** — produce a deletion plan: `path | class | size | age`.
   Anything outside the approved classes is reported but never scheduled.
4. **Confirm** — post the plan to the gateway; require explicit
   confirmation (risk_level high ⇒ mandatory per `agent-policy.yaml`).
5. **Execute** — delete only confirmed paths; re-measure afterwards.
6. **Report** — space reclaimed per filesystem; store summary in memory
   namespace `ops.cleanup`.

## Constraints

- Never delete: databases, backups, user data, config, or anything under
  version control.
- Dry-run first: the plan must be reproducible from the confirmation
  message alone.
- Abort and escalate via `incident-triage.md` if any deletion errors occur.

## Output

Deletion plan (pre-confirmation) and reclamation report (post-execution).
