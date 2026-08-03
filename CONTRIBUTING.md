# Contributing to jol-hermes-agents

Thanks for helping keep Hermes reliable. This repository is config-first:
most contributions are YAML, Markdown skills, or prompts rather than Python.

## Ways to contribute

- **Skills** — add or improve a skill under `skills/<domain>/`. Follow the
  frontmatter contract enforced by `tests/test_skills.py`.
- **Config** — changes under `config/` must keep the EU-only routing
  guarantee and use `${ENV_VAR}` references instead of literal secrets.
- **Memory** — schema or retention changes require an updated DPIA review
  (see `docs/dpia-ai-processing.md`).
- **Docs/runbooks** — operational knowledge belongs in `docs/`.

## Local workflow

```bash
make setup validate lint test
```

Or use `scripts/local-validate.sh`, which runs the same checks as CI.

## Commit & PR conventions

- One logical change per PR; keep diffs reviewable.
- Skill files: `kebab-case.md`, frontmatter required (`id`, `name`,
  `description`, `domain`, `risk_level`).
- Config changes: explain the blast radius in the PR description.
- Never commit `.env`, tokens, or customer data. CI rejects these.

## Review requirements

- Config, memory, and policy changes require review from a CODEOWNER.
- Behaviour-affecting prompt changes need a smoke test
  (`scripts/smoke-test.sh`) attached to the PR.

## Code of conduct

Be precise, be kind, prefer correctness over speed.
