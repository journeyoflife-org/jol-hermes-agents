# Data flow — where data enters, moves, and exits

## Categories

| Class | Examples | Handling |
|---|---|---|
| Operational telemetry | logs, metrics, disk usage, backup listings | processable; redact before gateways |
| Personal data (staff) | names, chat IDs, task assignees | minimised; retention-bound |
| Personal data (customers) | CRM content | never enters memory; referenced by ID only |
| Secrets | tokens, keys, passwords | env-only; never in repo, prompts, memory, logs |

## Flows

```
Telegram message ──ACL──► orchestration ──prompt (PII/secret-stripped)──► EU LLM provider
     ▲                        │                                              │
     │                        ├─ read-only queries ──► JOL infra             │
     │                        │                                              │
     └── redacted reply ◄─────┤◄───────────── completion ◄──────────────────┘
                              ├─ schema-checked write ──► memory store (retention-bound)
                              ├─ metadata-only ──► audit log
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
6. **Audit log**: metadata only (timestamp, skill id, provider, duration,
   status) — never full prompts or completions.

## Retention summary

See `memory/retention-policy.yaml`. Bitrix24 is the source of truth for
tasks/notifications; Hermes keeps metadata for 30 days only.
