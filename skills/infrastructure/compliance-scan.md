---
id: infra.compliance-scan
name: Compliance scan
description: Scan JOL infrastructure and configs for policy and GDPR compliance drift.
domain: infrastructure
risk_level: medium
owner: ops
---

# Compliance scan

## Purpose

Detect drift from JOL's compliance baseline: EU data residency, secret
hygiene, retention adherence, and configuration hardening.

## When to run

- Weekly scheduled scan.
- Before any release touching `config/`, gateways, or memory.
- On demand: "compliance scan" / "GDPR check".

## Checks

1. **EU residency** — every LLM provider in `config/model-routing.yaml`
   has an EU region; no endpoint points outside the EU.
2. **Secret hygiene** — no literal secrets in the repo (same ruleset as CI
   secret scan); all config uses `${ENV_VAR}` references.
3. **Retention** — every memory namespace in `memory/schema.yaml` has a
   retention rule in `memory/retention-policy.yaml`; purge jobs ran on time.
4. **Gateway ACLs** — Telegram `allowed_chat_ids` is non-empty (deny-by-
   default); confirmation threshold ≥ medium.
5. **Audit logging** — skill invocations and provider metadata are logged.

## Constraints

- Read-only: the scan reports drift, it never auto-fixes.
- Findings with personal data must be reported as counts/references, never
  as raw values.

## Output

Severity-ordered finding list: `severity | check | detail | remediation`,
plus a compliance scorecard. High/CRITICAL findings auto-create a Bitrix24
task via `bitrix/task-create.md`.
