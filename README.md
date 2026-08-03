# jol-hermes-agents

Hermes is the JOL operations agent: a config-first, skill-driven assistant that
runs against EU-only LLM providers and talks to the team through messaging
gateways (Telegram today). This repository holds everything declarative about the
agent — configuration, skills, memory schema, prompts, and the guardrail
policies — plus the tests that keep them honest.

## Repository layout

```
config/          Agent configuration (hermes.yaml, model routing, gateways)
skills/          Markdown skills grouped by domain (infrastructure, operations, bitrix)
memory/          Memory structure definition and GDPR retention policy
context/         Project context injected into the agent (AGENTS.md)
prompts/         System / master / operational prompts
tests/           Skill and memory-schema enforcement tests
scripts/         Local validation, lint, smoke test
docs/            Architecture, threat model, data flow, runbooks, DPIA
.github/         CI: lint + skill tests + secret scan, compliance check, CodeQL
```

## Design principles

1. **Config-first.** Agent behaviour is declared in YAML under `config/`;
   code only loads and validates it.
2. **EU data residency.** `config/model-routing.yaml` pins an EU-only LLM
   provider chain. Requests must never route outside the EU.
3. **GDPR by default.** `memory/retention-policy.yaml` defines what is kept
   and what is purged; memory writes must conform to `memory/schema.yaml`.
4. **Skills are contracts.** Every skill file carries YAML frontmatter and is
   validated in CI (`tests/test_skills.py`).
5. **No secrets in the repo.** Configuration uses env-var references
   (`${ENV_VAR}`); only `config/example.env` is committed. CI runs a secret
   scan on every push.

## Quick start

```bash
make setup      # create .venv and install dev dependencies
make validate   # validate config/, skills/, memory schema
make lint       # ruff + yamllint-style checks
make test       # run the test suite
```

Copy `config/example.env` to `.env` (never committed) and fill in the values
for your environment before running the agent.

## Documentation

- [Architecture](docs/architecture.md) — how Hermes fits into JOL
- [Data flow](docs/data-flow.md) — where data enters, moves, and exits
- [Threat model](docs/threat-model.md)
- [DPIA: AI processing](docs/dpia-ai-processing.md)
- [Runbooks](docs/runbooks/)

## Security

See [SECURITY.md](SECURITY.md) for the vulnerability reporting process. All
incidents involving agent behaviour are triaged with
[`skills/infrastructure/incident-triage.md`](skills/infrastructure/incident-triage.md).

## License

MIT — see [LICENSE](LICENSE).
