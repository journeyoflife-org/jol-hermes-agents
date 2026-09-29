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
- Documentation corrected to match the manual-only CI reality introduced by
  PR #12. `README.md`, `SECURITY.md`, `CONTRIBUTING.md`,
  `docs/architecture.md` and `docs/runbooks/operating-hermes.md` each still
  asserted that CI enforces controls automatically — "CI runs a secret scan on
  every push", "Every push is scanned for secrets", "CI rejects these",
  "CI fails the build on drift", "CI ... must be green". None of those runs on
  a push or a PR any more. Each claim is restated as what actually executes:
  the local `scripts/local-validate.sh` gate, with the workflows available on
  demand via `gh workflow run <name>`.
