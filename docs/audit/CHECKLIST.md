# 100% Go-Live Checklist — jol-hermes-agents

Audit date: 2026-08-13 · commit `dc79827`.
Legend: `[x]` verified during this audit · `[ ]` open gate · `[~]` blocked on
runtime (future runtime repo, not yet created; C1 resolved 2026-09-19). Findings reference `AUDIT_REPORT.md`.

## Phase 1 — repository audits

- [x] Directory tree mapped; all 55 tracked files reviewed (`git ls-files`)
- [x] Config set present & internally consistent: `config/hermes.yaml`,
      `config/model-routing.yaml`, `config/agent-policy.yaml`,
      `config/gateway/telegram.yaml` (`main.py validate` exit 0)
- [x] `SOUL.md` equivalent: `prompts/system-prompt.md` + `context/AGENTS.md` (I1)
- [x] `MEMORY.md` equivalent: `memory/schema.yaml` + `memory/retention-policy.yaml`
- [x] `USER.md` equivalent — judged not needed (2026-09-29): team-scoped ops agent; requester identity is the gateway chat-ID ACL
- [x] Manifest: `pyproject.toml` (Python ≥3.12, `pyproject.toml:6`); no lock file (L5-adjacent)
- [x] `Dockerfile` + `docker-compose.yml` + `.dockerignore` — landed & build-verified (H3, remediation log)
- [x] `.env.example` equivalent committed & gitignored: `config/example.env`, `.gitignore:14-18`
- [x] `scripts/` present: `local-validate.sh`, `lint.sh`, `smoke-test.sh`
- [x] `skills/` valid: 7 skills, frontmatter contract enforced (`tests/test_skills.py`)
- [x] `install.sh` idempotent bootstrap with version gate (I6) — verified by re-run; Windows `install.ps1` N/A (Linux target)
- [ ] `sessions/`, `state.db`, `cron/`, `logs/` paths defined — runtime concern (C1)
- [x] Dependency CVE review: 2 runtime + 3 dev deps, no known CVEs at audit time; Dependabot weekly
- [x] No hardcoded secrets (gitleaks CI + local scan clean)
- [x] No `eval`/`exec`/`shell=True`; only safe YAML loading (`SECURITY_POSTURE.md` §6)
- [x] Approval policy: autonomy levels + forbidden list + confirmation gate (I3)
- [x] Docker security hardening — compose: `read_only`, `cap_drop: ALL`, `no-new-privileges`, limits; container runs as uid 10001 (build-verified)
- [x] EU-only routing validated 3 ways (validator, compliance workflow, tests); CI workflows converted to manual-only (`workflow_dispatch`) to preserve GitHub Actions minutes (2026-09-29 constraint) — all checks still run locally via `scripts/local-validate.sh` + pre-commit

## Phase 2 — LLM connections

- [x] Provider keys referenced via env vars only (`config/model-routing.yaml:14,22`)
- [x] No plaintext secrets in tracked files
- [ ] `.env` populated with valid keys on target host — operator step
- [x] Context window ≥64k declared and CI-enforced (`context_length`, pinned model IDs — H2 fixed); provider-side re-verify at go-live
- [ ] Tool-calling capability verified per provider
- [~] `hermes chat -q "reply ok" --no-tools` passes — **blocked: no runtime (C1)**
- [x] Telegram gateway config: token env, ACL key, rate limit, redaction (`config/gateway/telegram.yaml`)
- [x] ACL format contract defined (CSV of numeric chat IDs, deny-all, refuse-to-start); runtime non-empty assertion remains a runtime gate (H1)
- [ ] MCP servers / built-in tool audit — N/A for this repo; re-scope to runtime
- [~] Provider failover test (blocked primary simulation) — blocked on runtime (C1)

## Phase 3 — smoke tests (all require runtime attachment)

- [~] CLI identity smoke test (agent name/model/time)
- [~] Tool execution test (sandboxed file write + approval prompt)
- [~] Memory persistence across sessions (`ops.*` namespace round-trip)
- [~] Skill creation/indexing test
- [~] Gateway latency <5 s + session continuation
- [~] Cron job registration + delivery (`scheduled-morning-run.md` path)
- [~] Destructive-command sandbox test (mandate constraint)
- [x] Repo-level suite: `main.py validate`, `pytest` (41/41 as of 2026-09-29), `lint.sh`, `smoke-test.sh` — all exit 0

## Security hardening gate

- [x] `.env` permissions `600` — enforced on audit host 2026-09-29 (`stat` verified); repeat on every deploy target
- [x] `config/` contains no plaintext secrets
- [x] Approval never "off" — level 3 disabled, gates on ≥level 2 (`config/agent-policy.yaml:36-50`)
- [ ] Sandbox backend for tool execution decided & tested (runtime decision)
- [ ] Telegram `allowed_chat_ids` populated and verified non-empty (operator + runtime gate)
- [x] Memory store backup tooling: `scripts/backup_memory.py` (sqlite backup API + `integrity_check`, M8); run it as deploy step 0 and before Curator/GEPA
- [x] Log rotation configured (`deploy/logrotate-hermes`, M7)
- [ ] SSH/Docker exposure: fail2ban or firewall rules on host
- [x] No telemetry/external leakage in shipped source (verified by code scan)
- [x] `SECURITY.md` reporting channel: GitHub private advisories documented (M3); org admin must enable private vulnerability reporting (gate noted in file)

## Documentation & governance

- [x] Audit artefacts published: `docs/audit/AUDIT_REPORT.md`,
      `DEPLOYMENT_GUIDE.md`, `SECURITY_POSTURE.md`,
      `LLM_CONNECTIVITY_MATRIX.md`, this `CHECKLIST.md`
- [x] Runbooks: deploy, rotate secrets, kill switch, rollback
      (`docs/runbooks/operating-hermes.md`)
- [x] Threat model + data flow + DPIA on file (`docs/`)
- [x] Release tag cut: `v0.1.0` (2026-09-29, post-remediation round 2)
- [x] Pin gitleaks image tag `v8.30.0` (M1)
- [x] Pin GitHub Action SHAs (M2) — all actions SHA-pinned 2026-09-29 at verified current majors (checkout/setup-python v7, codeql-action v4); Qodana removed entirely upstream (PR #10 deleted `qodana.yaml`; deletion accepted in merge resolution)
- [x] Single CODEOWNERS source of truth (N1) — root file merged with fine-grained rules, teams verified via `gh api`; stale `.github/CODEOWNERS` removed

## Monitoring, backup & DR

- [ ] Alerting on `provider_chain_exhausted` escalation
      (`config/agent-policy.yaml:90-93`) wired in runtime
- [x] Retention purge tool implemented: `scripts/retention_purge.py` (hard_delete namespaces; `anonymise` explicitly runtime-owned, M5)
- [ ] Purge job scheduled (host cron, `daily` per policy) + monitored
- [x] Backup of memory store (`scripts/backup_memory.py`); `skills/` snapshot = git tag/commit (M8)
- [ ] Restore drill scheduled per `skills/infrastructure/backup-verify.md`

## Release decision

- **Gate count (post-remediation round 3, 2026-09-29)**: 39 passed · 10 open ·
  9 deferred to the future runtime repo
- **Verdict**: CONDITIONAL GO as declarative definition repo. C1 resolved
  2026-09-19: `jol-hermes-agents` is definition-only; runtime readiness gate
  moves to future runtime repo. No runtime repo exists in the fleet today.
  Round 1 closed: C2 contract, H1, H2, H3, H4, M1, M4, M6, M7, I6, L2.
  Round 2 (2026-09-29) closed: M2 (action SHAs), M3 (reporting channel),
  M5 (purge tool), M8 (backup tool), L1 (dotenv used), L4/N1 (CODEOWNERS
  merged, teams verified), `.env` 600.
  Round 3 (2026-09-29): CI workflows converted to manual-only
  (`workflow_dispatch`) to preserve GitHub Actions minutes; all checks
  covered locally by `scripts/local-validate.sh` + pre-commit.
  Remaining opens are operator/org gates (`.env` values, tool-calling
  verification, fail2ban, purge scheduling, restore drill).
  See `AUDIT_REPORT.md` → "Remediation log".
