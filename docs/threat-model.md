# Threat model — Hermes

Method: lightweight STRIDE per trust boundary. Review on every gateway,
provider, or policy change.

## Trust boundaries

| # | Boundary | Entering side is... |
|---|---|---|
| B1 | Telegram → Hermes | untrusted human input |
| B2 | Hermes → LLM providers | trusted EU vendors, but data leaves our perimeter |
| B3 | Hermes → JOL infra | agent holds elevated access |
| B4 | Hermes → Bitrix24 | write access to organisational data |
| B5 | Repo → Hermes | config/skills are code: whoever merges, shapes behaviour |

## Key threats and controls

| Threat | Boundary | Impact | Controls |
|---|---|---|---|
| Prompt injection via Telegram message | B1 | agent executes attacker intent | gateway ACL (deny-by-default), risk gate + mandatory confirmation for mutating actions, skills constrain allowed steps |
| Data exfil via LLM provider | B2 | PII/secrets leave EU or leak | EU-only chain, `blocked_data_classes`, PII/secret stripping before provider calls, DPAs |
| Secret leakage in replies/logs | B1–B4 | credential disclosure | redaction patterns in gateway config, `redact_pii`, metadata-only audit logging, CI secret scan |
| Abuse of infra access | B3 | destruction/data loss | read-only default, confirmation for mutations, 2nd factor for deletion, disk-cleanup allowlist |
| Supply chain via repo | B5 | malicious skill/config merged | CODEOWNERS review for config/memory/policy, CI validation + secret scan + CodeQL |
| Bitrix24 spam/abuse | B4 | noise, task spam | rate limits, idempotency check, metadata-only memory |
| Memory over-retention | internal | GDPR violation | retention-policy coverage enforced by tests, daily purge job |

## Explicit non-goals (accepted risks)

- Hermes is not an authentication authority; gateway ACL is coarse
  (chat-ID based). Accepted while the operator group is small.
- No encrypted memory at rest in v0 (store is local, operator-managed).

## Review cadence

- Re-run this review on: new gateway, new provider, new high-risk skill,
  policy change, or after any SEV1/SEV2 incident involving the agent.
