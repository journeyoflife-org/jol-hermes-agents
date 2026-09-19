# Security Posture — jol-hermes-agents

Audit date: 2026-08-13 · commit `dc79827`. Traceable controls only;
each claim cites the implementing file.

## 1. Secrets management strategy

| Control | Status | Evidence |
|---|---|---|
| Zero secrets in repo | enforced | `${ENV_VAR}` references only; `config/hermes.yaml:2`, `config/model-routing.yaml:14,22`, `config/gateway/telegram.yaml:6,10` |
| Template committed, real `.env` ignored | enforced | `config/example.env` (value-free); `.gitignore:14-18` |
| CI secret scan on every push | enforced | gitleaks CLI, `.github/workflows/ci.yaml:42-49`; local approximation `scripts/lint.sh:15-22` |
| Pre-commit secret scan | enforced | gitleaks hook, `.pre-commit-config.yaml:26-29` |
| File permissions | **to do at deploy** | `.env` must be `600`; no `auth.json` concept in this repo (see `AUDIT_REPORT.md` I1) |
| Rotation procedure | documented | `docs/runbooks/operating-hermes.md:11-19` |
| Secrets stripped from outbound messages | declared | redaction patterns, `config/gateway/telegram.yaml:20-25`; pre-send checklist item 1, `prompts/validation-prompts/pre-send-checklist.md:6` |
| Secrets never enter LLM prompts | declared | `config/agent-policy.yaml:59` (`secrets_in_prompts: deny`); `blocked_data_classes: [credentials, payment_data]`, `config/model-routing.yaml:33-35` |

Gap: `config/example.env:13` default memory path is repo-relative (M6);
`${ENV_VAR}` interpolation itself is a runtime contract not implemented in
this repo (C2).

## 2. Command approval policy

There is no literal `approval.mode` key; the functional equivalent:

| Mandate requirement | Implementation | Evidence |
|---|---|---|
| Approval never `off` in production | Autonomy level ≥2 requires approval; level 3 disabled | `config/agent-policy.yaml:36-50` |
| Dangerous pattern/action list populated | 7 forbidden actions, incl. `exfiltrate_data`, `disable_security_controls` | `config/agent-policy.yaml:66-73` |
| Mutating infra needs confirmation | `mutating_infrastructure: require_confirmation` | `config/agent-policy.yaml:62` |
| Deletion needs confirmation + second factor | `data_deletion: require_confirmation_and_second_factor` | `config/agent-policy.yaml:63` |
| Gateway-level gate | `confirmation_required_above: medium` | `config/gateway/telegram.yaml:12` |
| Skill-level risk gate | low→execute, medium→announce, high→plan+confirm | `prompts/master-prompt.md:11-14` |
| Uncertainty escalation | `min_confidence_to_act: 0.8` | `config/agent-policy.yaml:77` |

Sensitive-env stripping for `execute_code`/`terminal` tools: not assessable —
no tool execution code exists in this repo (C1). Flagged as a runtime gate.

## 3. Container isolation boundaries

- **Present**: none in this repo (no Dockerfile/compose — H3). Proposed
  hardening (`read_only`, `cap_drop: ALL`, `no_new_privileges`,
  `pids_limit: 512`, custom bridge network) is specified in
  `DEPLOYMENT_GUIDE.md` §5.
- **Declared intent**: destructive skills are allowlist-based and
  confirmation-gated regardless of container backend
  (`skills/operations/disk-cleanup.md:25-35`); restore drills confined to
  scratch space (`skills/infrastructure/backup-verify.md:36-37`).
- `docker_forward_env` whitelist: N/A until packaging exists; mandate
  requires an explicit list, never wildcard.

## 4. Network ingress/egress rules

| Direction | Allowed | Evidence |
|---|---|---|
| Egress → LLM | EU endpoints only: Mistral (FR), OVH AI (FR) | `config/model-routing.yaml:9-24`; region allowlist `{eu, eu-central, eu-west}`, `main.py:37` |
| Egress → messaging | Telegram Bot API (polling; no inbound port needed) | `config/gateway/telegram.yaml` |
| Egress → Bitrix24 | webhook API only, env-sourced URL | `skills/bitrix/crm-notify.md:33` |
| Ingress | none required | polling model |
| Non-EU routing | prohibited + CI-blocked | `config/agent-policy.yaml:70`, `.github/workflows/compliance-check.yml:39-48` |
| Provider fallback | only on `timeout / rate_limited / server_error` | `config/model-routing.yaml:27-31` |

## 5. Audit log locations & content policy

- Skill invocations: logged, `log_every_skill_invocation: true`,
  `config/agent-policy.yaml:100`.
- Provider calls: `metadata_only` — never full prompt/completion,
  `config/agent-policy.yaml:101`.
- PII redaction in logs: `redact_pii: true`, `config/hermes.yaml:41`.
- Physical log paths: not defined in this repo (runtime concern, M7);
  proposed in `DEPLOYMENT_GUIDE.md` §6 (`/var/log/hermes/{agent,errors}.log`).

## 6. Code & supply-chain posture

| Check | Result |
|---|---|
| `eval`/`exec`/`shell=True`/`os.system` in shipped code | none (only `subprocess.run` with list argv in `tests/integration/test_validate_cli.py:13`) |
| YAML parsing | `yaml.safe_load` everywhere (`main.py:42`) |
| Network/telemetry in shipped code | none |
| Path traversal / SQL injection surface | none (no file-op or SQL code shipped) |
| CI permissions minimised | `permissions: contents: read` at job level; CodeQL scoped `security-events: write` (`.github/workflows/codeql.yml:10-20`) |
| Dependabot (pip + actions, weekly) | `.github/dependabot.yml` |
| CODEOWNER review on behaviour-shaping paths | `.github/CODEOWNERS` |
| CodeQL + Qodana static analysis | `.github/workflows/codeql.yml`, `qodana.yaml` (`failThreshold: 0`) |
| Residual supply-chain gaps | unpinned gitleaks `:latest` (M1), major-tag actions (M2) |

## 7. GDPR posture (declared controls)

- Retention rule per namespace, mechanically expressible, test-enforced:
  `memory/retention-policy.yaml`, `tests/test_memory_schema.py:62-77`.
- Data-subject rights: erasure ≤30 days, JSON export
  (`memory/retention-policy.yaml:40-46`).
- Prohibited content classes in memory
  (`memory/schema.yaml:62-66`), mirrored as routing `blocked_data_classes`.
- DPIA on file: `docs/dpia-ai-processing.md`, template `docs/DPIA-template.md`.
- Enforcement gap: the daily purge job itself is not implemented in this
  repo (M5) — control is documentary until the runtime/purge tool is audited.

## 8. Known accepted risks (from threat model)

- Coarse chat-ID-based ACL accepted for a small operator group
  (`docs/threat-model.md:28-31`) — conditioned on H1 (type contract) fix.
- No encrypted memory at rest in v0 (`docs/threat-model.md:32`).
