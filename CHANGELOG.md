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

### Changed
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
