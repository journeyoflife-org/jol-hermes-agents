# DPIA — AI-assisted operational processing (Hermes)

Data Protection Impact Assessment per Art. 35 GDPR.
Status: **draft v0.2** — must be reviewed by the data protection officer /
responsible person before production use. No DPO is appointed; the repository
owner is the responsible person (see §6).

## 1. Processing description

| Item | Value |
|---|---|
| Controller | JOL (contact: TBD) |
| System | Hermes operations agent |
| Purpose | Infrastructure monitoring, incident triage, operational reporting, task follow-up |
| Legal basis | Art. 6(1)(f) legitimate interest (internal IT operations); staff data additionally employment context rules where applicable |
| Data subjects | JOL staff (names, chat IDs), incident reporters; customers only by reference ID |
| Data categories | Operational telemetry, staff identifiers, no special categories (Art. 9) by design |

## 2. Necessity and proportionality

- Memory is limited to eight schema-defined namespaces
  (`memory/schema.yaml`); each has a bounded retention period
  (`memory/retention-policy.yaml`), and the pairing is enforced by
  `main.py:222-237` and `tests/test_memory_schema.py:62-67`.
- Six namespaces hold operational output. Two (`audit.events`,
  `audit.approvals`) hold **accountability evidence** required by Art. 5(2)
  and by the `audit:` block of `config/agent-policy.yaml`. They store
  metadata only: never prompt or completion bodies.
- Audit records identify the acting principal by a pseudonymous label
  (`principal_ref`), not by raw Telegram chat ID, so the accountability trail
  does not duplicate the identifier already held in the gateway ACL.
- Customer content is never copied into agent memory — references by ID only.
- LLM processing is confined to an EU-only provider chain with DPAs;
  blocked data classes (credentials, payment data) are never transmitted.

## 3. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| PII leak via LLM provider | low | high | EU-only chain, PII stripping, DPAs, blocked data classes |
| Over-retention | low | medium | retention rules enforced in tests + daily purge job |
| Unauthorised access to memory store | low | medium | local store, host-level ACL, kill switch runbook |
| Prompt injection leading to data disclosure | medium | high | gateway ACL, confirmation gates, redaction, pre-send checklist |
| Secret disclosure | low | high | env-only secrets, redaction, CI secret scan |
| Audit trail becomes a new personal-data store | medium | medium | `principal_ref` pseudonymised; metadata-only fields; 730-day bound; `hard_delete`, which is mechanically executable (`anonymise` namespaces are skipped by `scripts/retention_purge.py` as runtime-owned) |
| Declared control with no evidence — unauditable | medium | high | `control_definitions` in `config/agent-policy.yaml` names every control; gated actions write `audit.approvals` before execution |

## 4. Data subject rights

- Erasure: `hard_delete_by_reference` within 30 days (see retention policy).
- Access: JSON export of all records referencing the subject.

## 5. Review triggers

New provider, new gateway, new memory namespace, new high-risk skill, or
any SEV1/SEV2 incident involving personal data requires re-assessment.

## 6. Revision record

| Date | Version | Trigger | Change | Assessed by | Formal sign-off |
|---|---|---|---|---|---|
| 2026-08-13 | v0.1 | initial draft | Baseline assessment | — | outstanding |
| 2026-09-29 | v0.2 | new memory namespaces (§5 trigger) | Added `audit.events` and `audit.approvals`; necessity and proportionality re-assessed in §2; two risks added in §3 | repository owner (sole operator) | **outstanding** — no DPO exists |

No sign-off is claimed here that did not occur. While the status remains
*draft*, this document is evidence that an assessment was performed, not
evidence that it was approved.
