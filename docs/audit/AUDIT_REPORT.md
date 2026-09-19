# Audit Report — jol-hermes-agents

- **Scope**: `journeyoflife-org/jol-hermes-agents`, commit `dc79827` (main, clean tree)
- **Date**: 2026-08-13
- **Auditor role**: Senior DevOps/ML Engineer & Security Auditor
- **Method**: file-by-file review of all 55 tracked files + live execution of the
  validation suite (`main.py validate`, `pytest`, `scripts/lint.sh`,
  `scripts/smoke-test.sh`)

## Executive summary

The repository is a **declarative agent definition** (config, skills, memory
schema, prompts, guardrail policy) plus a **validator** (`main.py`). It is
internally consistent, well-tested (27/27 tests pass), secret-free (verified
by CI gitleaks + local scan), and has an unusually strong GDPR/compliance
posture for a v0.1.0 project.

However, measured against the mandate of *100% operational readiness with LLM
connectivity fully validated*, the repo is **not go-live ready as-is**: there
is no runtime in this repository, no container/service packaging, and no way
to execute the mandated LLM smoke tests. Details below; Go/No-Go at the end.

Live evidence collected during this audit:

```text
$ .venv/bin/python main.py validate
OK    config, skills and memory schema are valid          (exit 0)

$ .venv/bin/python -m pytest
27 passed in 0.15s                                        (exit 0)

$ bash scripts/lint.sh
ruff: All checks passed / yamllint clean / secret scan clean (exit 0)

$ bash scripts/smoke-test.sh
smoke-test: OK                                            (exit 0)
```

---

## CRITICAL (blocks deployment)

### C1. No runtime orchestration exists in this repository
- Evidence: `main.py:1-10` states "Runtime orchestration lives elsewhere";
  `main.py:139-144` shows the `hermes` console script
  (`pyproject.toml:21`) only prints usage or runs `validate`.
- Impact: **none** of the mandated Phase 2/3 smoke tests are executable from
  this repo: `hermes chat -q ...` (LLM connectivity), tool execution, memory
  persistence, gateway latency, cron, and provider failover all have no
  implementation here. LLM connectivity **cannot be validated**; it can only
  be *declared* (`config/model-routing.yaml`).
- Required: either the runtime repo/component is identified and audited with
  this config set mounted into it, or this repo is declared "definition only"
  and the readiness gate moves to the runtime repository.

### C2. `${ENV_VAR}` interpolation is declared but implemented nowhere
- Evidence: `${HERMES_MEMORY_PATH}` (`config/hermes.yaml:27`),
  `${HERMES_TELEGRAM_BOT_TOKEN}` (`config/gateway/telegram.yaml:6`),
  `${HERMES_TELEGRAM_ALLOWED_CHAT_IDS}` (`config/gateway/telegram.yaml:10`),
  `${HERMES_PRIMARY_API_KEY}` / `${HERMES_FALLBACK_API_KEY}`
  (`config/model-routing.yaml:14,22`). `python-dotenv` is declared
  (`pyproject.toml:10`) but imported nowhere in the codebase.
- Impact: if the consuming runtime does not implement the same interpolation
  contract, secrets either fail closed (best case) or — worse — the literal
  string `${HERMES_TELEGRAM_ALLOWED_CHAT_IDS}` is treated as an ACL value
  with undefined semantics (see H1).
- Required: document the interpolation contract in `docs/data-flow.md` or a
  `docs/config-contract.md`, and add a validator check that every `${VAR}`
  used in `config/` appears in `config/example.env`.

---

## HIGH (must fix before go-live)

### H1. Gateway ACL type contract is undefined
- Evidence: `config/gateway/telegram.yaml:9-10` — comment says
  "Empty list = deny all", but the value is a single env-var placeholder
  string, not a list. No code anywhere parses CSV→list or asserts non-empty.
- Impact: ACL behaviour (deny-all vs. open bot) depends on an unimplemented
  runtime interpretation. An open Telegram bot is an explicit security
  violation of `docs/threat-model.md` (B1).
- Fix: define the format (e.g. comma-separated chat IDs), validate non-empty
  at startup, and add the check to `main.py validate` for a local override
  file.

### H2. Model identifiers are unpinned
- Evidence: `config/model-routing.yaml:13` (`mistral-large-latest`),
  `:21` (`llama-3.1-70b-instruct`).
- Impact: violates the mandate constraint "ALWAYS pin model versions";
  `-latest` aliases can change context window, pricing, and tool behaviour
  silently. No `context_length` override exists, so the ≥64k requirement is
  asserted by vendor documentation only (both candidates are 128k-capable;
  see `LLM_CONNECTIVITY_MATRIX.md`).
- Fix: pin dated/snapshotted model IDs and add explicit `context_length`
  keys validated by `main.py`.

### H3. No container or service packaging
- Evidence: no `Dockerfile`, `docker-compose.yml`, `.dockerignore`, systemd
  unit, or install script among the 55 tracked files (`git ls-files`).
- Impact: the entire mandated Docker hardening checklist (`read_only`,
  `cap_drop: ALL`, `no_new_privileges`, PID limits, env whitelist) and the
  systemd checklist (`Restart=on-failure`, `EnvironmentFile`, dedicated
  user) have nothing to attach to. Templates are proposed in
  `DEPLOYMENT_GUIDE.md` but are not part of the repo yet.
- Fix: land packaging artefacts in this repo (or the runtime repo) and audit
  them against §3.2/§3.3 of the mandate.

### H4. `make lint` and `make setup` swallow failures
- Evidence: `Makefile:16` (`yamllint ... || true`), `Makefile:7`
  (`python3 -m venv .venv || true`).
- Impact: local developers get green results on broken YAML or a failed venv
  creation; CI is unaffected (`.github/workflows/ci.yaml:37` does not use
  `|| true`, and `scripts/lint.sh:13` fails properly), but the local/CI
  divergence hides issues pre-push.
- Fix: remove both `|| true` guards.

---

## MEDIUM (fix within 48h of deployment)

| # | Finding | Evidence | Fix |
|---|---|---|---|
| M1 | gitleaks image tag unpinned (`:latest`) — supply-chain risk | `.github/workflows/ci.yaml:47` | Pin digest or version tag (pre-commit already pins `v8.30.0`, `.pre-commit-config.yaml:27`) |
| M2 | Actions pinned to major tags, not SHAs | `.github/workflows/*.y*ml` (`checkout@v4`, `setup-python@v5`, `codeql-action@v4`, `qodana-action@v2026.1`) | Pin commit SHAs with comment |
| M3 | SECURITY contact is a placeholder | `SECURITY.md:13` (`security@jol.example`) | Replace before any public exposure |
| M4 | Frontmatter parser splits on `---` (maxsplit 2) | `main.py:52`, `tests/test_skills.py:23` | A skill body containing `---` (e.g. a YAML example) silently truncates/misparses; parse via first-closing-`---`-line rule or add a regression test |
| M5 | Retention purge is policy-only, no implementation | `memory/retention-policy.yaml:13` (`purge_schedule: daily`) | GDPR storage limitation currently rests on an external purge job; name and document that job, or the DPIA claim is unenforced |
| M6 | Default memory path is repo-relative | `config/example.env:13` (`./runtime/hermes-memory.sqlite`) | Production must use an absolute path on a persistent volume; state this in the example |
| M7 | No health-check / doctor / log-rotation artefacts | repo-wide | Add once runtime exists; see `CHECKLIST.md` |
| M8 | No automated backup for the memory store | `memory.store.path` (`config/hermes.yaml:27`) | Mandate requires snapshotting state before Curator/GEPA and first run; define in runbook |

---

## LOW (nice-to-have)

| # | Finding | Evidence |
|---|---|---|
| L1 | `python-dotenv` declared but unused in code | `pyproject.toml:10`; no import in `main.py` |
| L2 | `make clean` glob `**/__pycache__` requires `globstar` in bash | `Makefile:25` |
| L3 | No `.editorconfig`-driven CI check (file present, unenforced) | `.editorconfig` |
| L4 | `CODEOWNERS` org handle `@jol/...` unverified against actual GitHub org teams | `.github/CODEOWNERS:2-11` |
| L5 | `CHANGELOG.md` / version at 0.1.0 — mandate says pin release tags in production; no tag exists yet | `git log` (4 commits, no tags) |

---

## INFO (observations)

### I1. The repo deliberately deviates from the `~/.hermes/` reference layout
The mandate assumed a runtime state directory. This repo is the *source of
truth for declarations*; the mapping is:

| Reference layout | Equivalent in this repo |
|---|---|
| `SOUL.md` | `prompts/system-prompt.md` + `context/AGENTS.md` |
| `MEMORY.md` | `memory/schema.yaml` + `memory/retention-policy.yaml` |
| `USER.md` | not present (no per-user profile concept defined) |
| `config.yaml` | `config/hermes.yaml` + `config/agent-policy.yaml` + `config/model-routing.yaml` |
| `auth.json` / `.env` | `config/example.env` template; real values env-only |
| `state.db` | `${HERMES_MEMORY_PATH}` (sqlite) |
| `skills/*/SKILL.md` | `skills/<domain>/<skill>.md` with enforced frontmatter |
| `sessions/`, `cron/`, `logs/`, `plugins/` | runtime concerns — not represented (gap noted in C1) |

Deviation is by design (config-first, `docs/architecture.md:27-43`) and is
**acceptable** — but only if the runtime consuming these artefacts is
identified (C1).

### I2. Security scan of all Python source — clean
- No `eval`/`exec`/`os.system`; the only `subprocess` use is
  `tests/integration/test_validate_cli.py:13` (list argv, no `shell=True`).
- YAML parsed exclusively with `yaml.safe_load` (`main.py:42`,
  `tests/test_skills.py:24`, `tests/test_memory_schema.py:20`).
- No network calls, no telemetry, no file-write paths in shipped code —
  attack surface is minimal by construction.
- No hardcoded secrets: CI gitleaks + `scripts/lint.sh:15-22` naive scan
  both clean; `.env`/`.env.*` gitignored (`.gitignore:14-18`), only
  `config/example.env` committed (value-free template).

### I3. Command approval system — present in spirit, different key names
The mandate's `approval.mode` does not exist as a key. The functional
equivalent is:
- `config/agent-policy.yaml:13-54` — autonomy levels 0–3; level 3 disabled
  (`:50 enabled: false`), level ≥2 `requires_approval: true`.
- `config/gateway/telegram.yaml:12` —
  `confirmation_required_above: medium`.
- `config/agent-policy.yaml:66-73` — populated forbidden-action list.
This satisfies the *intent* of "never approval-off in production"; there is
no literal `approval.mode: off` anywhere.

### I4. EU-only routing is enforced three independent ways
`main.py:78-84` (validator), `.github/workflows/compliance-check.yml:39-48`
(CI assertion, also scheduled weekly), and
`tests/test_memory_schema.py:62-67`-style coverage for retention. Redundant
and correct.

### I5. Mandate-listed packages are not applicable
`dspy`, `fastapi`, `uvicorn`, `httpx`, `sqlalchemy`, `fts5` are absent —
correctly, since this repo ships no runtime. `pyyaml` + `python-dotenv`
runtime deps and `pytest`/`ruff`/`yamllint` dev deps are all unpinned
lower bounds; Dependabot covers pip + github-actions weekly
(`.github/dependabot.yml`). Python constraint `>=3.12`
(`pyproject.toml:6`) exceeds the 3.11+ requirement.

### I6. `install.sh`/`install.ps1` absent
`make setup` (`Makefile:6-9`) is the only bootstrap: creates a venv and
installs `.[dev]`. It does not manage Python version, Node, ripgrep, ffmpeg,
or Git, and is not idempotency-guarded beyond `|| true` (see H4). Acceptable
for a definition repo; insufficient for a runtime host.

---

## Go/No-Go recommendation

**NO-GO for "100% operational readiness with validated LLM connectivity" as
scoped by the mandate** — solely because the runtime is out of scope of this
repository (C1, C2, H3).

**CONDITIONAL GO for the repository's actual purpose** (declarative agent
definition + validation): the repo is internally consistent, tested,
secret-free, and compliance-strong. Gate items before merging into a
production runtime:

1. Resolve C1/C2 — identify the runtime, define the `${ENV_VAR}`
   interpolation contract.
2. Fix H1 (ACL type contract) and H2 (pin models + context_length).
3. Land H3 packaging artefacts (templates in `DEPLOYMENT_GUIDE.md`).
4. Re-run the full Phase 2/3 smoke suite *against the runtime* with this
   config set mounted.

See `CHECKLIST.md` for the trackable gate list.

---

## Remediation log (2026-08-13, same-day fixes, verified)

| Finding | Status | Fix & verification |
|---|---|---|
| C2 | **fixed (contract enforced)** | `validate_env_contract()` in `main.py` fails `validate` when any env var referenced in `config/` (`${VAR}` *and* `*_env` keys) is absent from `config/example.env`; 3 unit tests. Runtime interpolation itself remains a runtime-repo concern. |
| H1 | **fixed (contract defined)** | CSV-of-numeric-chat-IDs contract + deny-all + refuse-to-start requirement documented in `config/gateway/telegram.yaml:9-15`; runtime assertion still a runtime gate. |
| H2 | **fixed** | Primary model pinned to `mistral-large-2411`; `context_length: 128000` declared for both providers; validator rejects `*-latest` aliases and `context_length < 64000` (`check_provider_models`, 3 unit tests). |
| H3 | **fixed (verified by build)** | `Dockerfile` (uid 10001 non-root, healthcheck), `.dockerignore`, hardened `docker-compose.yml` (`read_only`, `cap_drop: ALL`, `no-new-privileges`, PID/CPU/memory limits, custom bridge, no published ports), `deploy/hermes.service`, `deploy/logrotate-hermes`. Verified: `docker build` OK; `docker compose config` OK; in-container `hermes validate` OK; `id` → `uid=10001(hermes)`; no write to `/etc`. |
| H4 / L2 | **fixed** | `Makefile:7,16` `\|\| true` removed; `clean` uses portable `find`. |
| M1 | **fixed** | gitleaks pinned to `v8.30.0` in `.github/workflows/ci.yaml:48` (matches pre-commit). |
| M4 | **fixed** | Line-based frontmatter parser tolerates `---` in bodies and rejects unterminated fences; regression tests added. |
| M6 | **fixed** | `config/example.env` default memory path is now an absolute volume path with local-dev note. |
| M7 (partial) | **fixed** | logrotate config shipped (`deploy/logrotate-hermes`). |
| I6 | **fixed** | `install.sh`: idempotent, Python ≥3.12 gate, fail-fast messages; re-run verified (`install: OK`). |
| C1 | **open** | Runtime orchestration still lives outside this repo — unchanged by design; gate stands. |
| M2, M3, M5, M8, L1, L3–L5 | **open** | Require org-level decisions (action SHA pins, real security contact, purge job implementation, backup tooling) — tracked in `CHECKLIST.md`. |

Post-remediation verification (all exit 0): `main.py validate` · `pytest`
**35 passed** (was 27) · `scripts/lint.sh` · `scripts/smoke-test.sh` ·
`scripts/local-validate.sh` · `./install.sh` (idempotent re-run) ·
`docker compose config` · `docker build` · in-container validate as
non-root user.
