# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial repository scaffold: config/, skills/, memory/, context/, prompts/,
  tests/, scripts/, docs/, and GitHub workflows (CI, compliance check, CodeQL).
- EU-only model routing configuration (`config/model-routing.yaml`).
- GDPR memory schema and retention policy (`memory/`).
- Skill validation and memory-schema enforcement tests.
- DPIA for AI processing (`docs/dpia-ai-processing.md`).
- Audit artefacts under `docs/audit/` (report, deployment guide, security
  posture, LLM connectivity matrix, go-live checklist).
- Production packaging: `Dockerfile` (non-root, healthcheck), `.dockerignore`,
  hardened `docker-compose.yml`, `deploy/hermes.service`,
  `deploy/logrotate-hermes`, and idempotent `install.sh`.
- Validator: env-var contract check (every env var referenced in `config/`,
  including `*_env` keys, must exist in `config/example.env`) and
  model-pinning + `context_length >= 64000` enforcement.
- Memory tooling (audit round 2): `scripts/retention_purge.py` executes the
  GDPR retention policy (hard_delete; `anonymise` reported as runtime-owned)
  and `scripts/backup_memory.py` snapshots the store via the sqlite backup
  API with `PRAGMA integrity_check`; both resolve `HERMES_MEMORY_PATH`
  through `.env` (python-dotenv).
- Governance: capability and agent-boundary review artefact
  (`docs/capability-review-prompt.md`) — the five scoping questions, a
  classification ladder (config contract → deterministic script → skill →
  agent → supervisor → separate repository), the minimum control set for
  agent-grade capabilities, and evidence rules. Linked from `README.md`.
- Accountability evidence namespaces `audit.events` and `audit.approvals`
  (`memory/schema.yaml`) with 730-day `hard_delete` retention
  (`memory/retention-policy.yaml`). `docs/dpia-ai-processing.md` re-assessed to
  v0.2 with a revision record, as its own §5 review trigger requires.
- `control_definitions` in `config/agent-policy.yaml`: what `confirmation`
  means, what counts as a `second_factor` (and why two LLM agents are one
  factor, not two), and the two deletion classes — scheduled retention purge
  versus ad-hoc/DSR deletion.

### Changed
- All GitHub Actions workflows (`ci.yaml`, `codeql.yml`, `compliance-check.yml`)
  converted to manual-only (`workflow_dispatch`) to preserve GitHub Actions
  minutes (insufficient budget for automated CI). Equivalent checks run
  locally via `scripts/local-validate.sh` + `.pre-commit-config.yaml`.
  Workflows preserved for on-demand use via `gh workflow run <name>`.
- All GitHub Actions pinned to commit SHAs at verified current majors
  (checkout/setup-python v7, codeql-action v4); Qodana CI job removal
  accepted (cost decision `7b49384`); `qodana.yaml` subsequently removed
  entirely by upstream PR #10 — deletion accepted in merge resolution.
- CODEOWNERS consolidated into the single root file (GitHub reads one file
  only; root wins). Fine-grained path rules preserved and mapped to verified
  org teams; every rule includes `@journeyoflife-org/security`.
- `SECURITY.md`: vulnerability reporting via GitHub private advisories
  (enablement gate noted); placeholder email marked do-not-use.
- `config/model-routing.yaml`: pinned primary model to `mistral-large-2411`
  (was the mutable `-latest` alias) and declared `context_length` per provider.
- `config/gateway/telegram.yaml`: documented the ACL contract (CSV of numeric
  chat IDs; empty = deny all; runtime must refuse to start when empty).
- `config/example.env`: production memory path is now an absolute volume path.
- `Makefile`: `setup` and `lint` no longer swallow failures; `clean` uses a
  portable `find`-based purge.
- Frontmatter parsing (`main.py`, `tests/test_skills.py`) is line-based and
  tolerates `---` horizontal rules inside skill bodies.
- CI secret scan pinned to `zricethezav/gitleaks:v8.30.0` (was `:latest`).
- `scripts/retention_purge.py` now fails closed: the deletion and its
  `audit.events` evidence row commit in one transaction, so a store without the
  audit table aborts with nothing deleted. Adds `--run-id`; dry runs write no
  evidence and identify their output as the `dry_run_reviewed` second-factor
  input. 3 new tests (44 total).
- Audit-evidence drift corrected: `docs/audit/LLM_CONNECTIVITY_MATRIX.md` and
  `docs/audit/DEPLOYMENT_GUIDE.md` still described H2 (unpinned models) and H3
  (no packaging) as open, contradicting the remediation log in
  `AUDIT_REPORT.md`. Both now state current reality, and §5/§6 of the
  deployment guide cite the canonical artefacts instead of duplicating
  divergent copies of them. The dated 2026-08-13 `AUDIT_REPORT.md` snapshot is
  intentionally unchanged.
- `docs/threat-model.md` re-reviewed, as its own review cadence requires
  (triggers: policy change and memory schema change). Three threats added —
  deletion without an evidence trail, the audit trail becoming a personal-data
  store, and audit evidence altered after the fact — the last recorded as an
  unenforced runtime gate rather than claimed as a control. A review log table
  now dates each re-review.
- `docs/data-flow.md`: rule 6 described the audit log as carrying `provider`
  and `duration`, fields that never existed in any declared schema, and omitted
  the principal and agent identity. It now matches `audit.events` /
  `audit.approvals`; an accountability-evidence data category and the 730-day
  audit retention are documented.
