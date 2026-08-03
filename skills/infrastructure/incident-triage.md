---
id: infra.incident-triage
name: Incident triage
description: Structured first response to an operational incident — scope, severity, next actions.
domain: infrastructure
risk_level: medium
owner: ops
---

# Incident triage

## Purpose

Given an alert or reported problem, produce a fast, structured triage:
what is broken, how bad it is, what to do next. Optimise for correctness of
the severity call, not speed of the reply.

## When to run

- On any monitoring alert, error burst, or user report of outage.
- Trigger phrases: "incident", "outage", "something is down".

## Steps

1. **Scope** — identify affected system(s), time window, and blast radius
   (which services/users depend on it).
2. **Evidence** — collect recent logs/metrics excerpts; redact secrets and
   personal data before including anything in a message.
3. **Severity classification**:
   - SEV1: customer-facing outage or data loss risk.
   - SEV2: degraded service, workaround exists.
   - SEV3: cosmetic / no user impact.
4. **Hypotheses** — top 3 likely causes ranked by evidence, each with a
   one-command verification step.
5. **Actions** — safe first actions only (restart, failover behind
   confirmation). Mutating actions require explicit confirmation per
   `config/agent-policy.yaml`.
6. **Communicate** — post triage summary to the ops channel; SEV1/SEV2 also
   create a Bitrix24 task via `bitrix/task-create.md`.

## Constraints

- Never execute destructive remediations autonomously.
- Preserve evidence: no log deletion or config changes during triage.
- If confidence in severity is below the policy threshold, escalate to a
  human rather than downgrading.

## Output

Structured triage card: `severity | scope | evidence summary | hypotheses |
recommended next actions`.
