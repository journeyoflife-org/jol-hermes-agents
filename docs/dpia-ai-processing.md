# DPIA — AI-assisted operational processing (Hermes)

Data Protection Impact Assessment per Art. 35 GDPR.
Status: **draft v0.1** — must be reviewed by the data protection officer /
responsible person before production use.

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

- Memory is limited to six schema-defined namespaces
  (`memory/schema.yaml`); each has a bounded retention period
  (`memory/retention-policy.yaml`).
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

## 4. Data subject rights

- Erasure: `hard_delete_by_reference` within 30 days (see retention policy).
- Access: JSON export of all records referencing the subject.

## 5. Review triggers

New provider, new gateway, new memory namespace, new high-risk skill, or
any SEV1/SEV2 incident involving personal data requires re-assessment.
