# Data flow — where data enters, moves, and exits

## Categories

| Class | Examples | Handling |
|---|---|---|
| Operational telemetry | logs, metrics, disk usage, backup listings | processable; redact before gateways |
| Personal data (staff) | names, chat IDs, task assignees | minimised; retention-bound |
| Personal data (customers) | CRM content | never enters memory; referenced by ID only |
| Secrets | tokens, keys, passwords | env-only; never in repo, prompts, memory, logs |
| Accountability evidence | run IDs, agent identity, tool names, outcomes | metadata only; pseudonymous principal; 730-day bound |

## Flows

```
Telegram message ──ACL──► orchestration ──prompt (PII/secret-stripped)──► EU LLM provider
     ▲                        │                                              │
     │                        ├─ read-only queries ──► JOL infra             │
     │                        │                                              │
     └── redacted reply ◄─────┤◄───────────── completion ◄──────────────────┘
                              ├─ schema-checked write ──► memory store (retention-bound)
                              ├─ metadata-only ──► audit namespaces (memory)
                              └─ webhook ──► Bitrix24 (tasks/notifications)
```

## Rules

1. **Inbound**: gateway ACL first; unknown chat IDs are dropped silently.
2. **To providers**: prompts are stripped of PII and secrets; data classes
   listed in `model-routing.yaml: blocked_data_classes` never leave.
3. **From providers**: completions are treated as untrusted input to
   orchestration, never as instructions executed directly.
4. **To memory**: only schema-defined namespaces/fields; retention applies
   from write time.
5. **To gateways**: every outbound message passes redaction patterns and
   the pre-send checklist (`prompts/validation-prompts/pre-send-checklist.md`).
6. **Audit evidence**: written to the `audit.events` and `audit.approvals`
   namespaces declared in `memory/schema.yaml` — metadata only, never full
   prompts or completions (`config/agent-policy.yaml`, `audit:` block). Each
   record carries the pseudonymous human principal, the agent identity, the
   skill, the autonomy level, the tools invoked, the data classes touched, the
   result and an evidence reference. Gated actions additionally record the
   approval method and second factor in `audit.approvals`.

## Retention summary

See `memory/retention-policy.yaml`. Bitrix24 is the source of truth for
tasks/notifications; Hermes keeps metadata for 30 days only. Audit evidence is
kept 730 days and hard-deleted — the same window as `compliance.findings`.

The retention purge job records its own execution in `audit.events` and fails
closed, deleting nothing, when that namespace is unavailable — so retention
enforcement is itself audited.
