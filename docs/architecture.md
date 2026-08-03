# Architecture — how Hermes fits into JOL

## Position

Hermes sits between three worlds:

```
        Humans                     Hermes                        Machines
  ┌─────────────────┐      ┌───────────────────────┐      ┌─────────────────┐
  │ Telegram (ops)  │◄────►│ Gateway layer         │      │ JOL infra       │
  │ Bitrix24 (tasks)│      │ Orchestration (skills)│◄────►│ (hosts, backups,│
  │                 │      │ Memory (GDPR-scoped)  │      │  logs, metrics) │
  └─────────────────┘      │ LLM routing (EU-only) │      └─────────────────┘
                           └───────────────────────┘
```

- **Gateways** accept human input and deliver output. Telegram is the live
  channel (`config/gateway/telegram.yaml`); Bitrix24 is used for durable
  follow-ups (tasks, notifications).
- **Orchestration** matches requests to skills and enforces the risk gate
  from `config/agent-policy.yaml`.
- **Memory** is schema-constrained and retention-bound; it is never the
  source of truth for operational data — the infrastructure itself is.
- **LLM routing** is a failover chain of EU providers
  (`config/model-routing.yaml`).

## Config-first principle

This repository deliberately contains almost no runtime code. Behaviour is
declared in:

| Artefact | Purpose |
|---|---|
| `config/hermes.yaml` | agent identity, paths, gateways, logging |
| `config/model-routing.yaml` | EU-only provider chain |
| `config/agent-policy.yaml` | guardrails, escalation, audit |
| `skills/**/*.md` | executable procedures (contracts) |
| `memory/*.yaml` | what may be persisted and for how long |
| `prompts/*.md` | system, master, operational and validation prompts |
| `context/AGENTS.md` | injected project context |

`main.py validate` and `tests/` keep these artefacts internally consistent;
CI fails the build on drift.

## Execution model

1. Gateway message → ACL check → rate limit.
2. Orchestration: classify → skill match → risk gate.
3. Skill execution: evidence gathering (read-only by default) → optional
   human confirmation → action.
4. Outputs: gateway reply (redacted) + memory write (schema-checked) +
   audit log (metadata only).

## Failure handling

- Provider failure: failover along the routing chain; if the whole chain is
  down, Hermes degrades to scripted/read-only mode and says so.
- Skill failure: stop on first hard error, report, never improvise around
  the contract.
- Uncertainty above threshold: escalate to a human (see
  `skills/infrastructure/incident-triage.md`).

## Security posture

See [threat-model.md](threat-model.md) and [data-flow.md](data-flow.md).
Key controls: EU-only routing, deny-by-default gateway ACLs, mandatory
confirmation for mutating actions, secret-free configuration, CI secret
scan + CodeQL.
