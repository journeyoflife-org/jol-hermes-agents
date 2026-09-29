# Deployment Guide — jol-hermes-agents

Status: **active runbook** — the packaging artefacts (audit finding H3) have
landed and are build-verified: `Dockerfile`, `docker-compose.yml`,
`.dockerignore`, `deploy/hermes.service`, `deploy/logrotate-hermes` (see the
remediation log at `AUDIT_REPORT.md:240`). This guide covers the declarative
repo plus the runtime boundary described in `AUDIT_REPORT.md` (C1).

> **Amendment (2026-09-29).** This guide was written while H2 (unpinned model
> IDs) and H3 (no packaging artefacts) were still open, and was not updated
> when they were remediated (H2: commit `6646790`, PR #8, 2026-09-20; H3:
> build-verified per `AUDIT_REPORT.md:240`). Corrected here: the status line,
> the pinned primary model, the test count (41 — verified by running `pytest`,
> not 27), stale `file:line` references, and §5/§6, which duplicated divergent
> copies of the artefacts and now cite the canonical files instead.
> Duplicating artefact content in prose is what caused this drift; the guide
> now names paths and verifies them by command.

> Convention: commands are exact; templated values use `<ANGLE_BRACKETS>`.
> Never commit real values — everything secret-shaped lives in `.env` /
> systemd `EnvironmentFile`, per `docs/runbooks/operating-hermes.md`.

---

## 1. Target environment specification

| Item | Requirement | Rationale |
|---|---|---|
| OS | Ubuntu 22.04+ / Debian 12+ / RHEL 9+ | mandate §3.1 |
| Python | ≥ 3.12 | `pyproject.toml:6` |
| RAM | 8 GB (API-based providers) | no local inference in `config/model-routing.yaml` |
| Disk | persistent volume for runtime state (`state.db`, logs) | C1/H3 |
| Network egress | HTTPS to `api.mistral.ai` + OVH AI endpoint (EU only) | `config/model-routing.yaml` |
| Network ingress | none required (Telegram uses long polling by default) | `config/gateway/telegram.yaml` |

## 2. Fresh install (validator / config repo)

```bash
git clone https://github.com/journeyoflife-org/jol-hermes-agents.git
cd jol-hermes-agents
make setup        # creates .venv, installs .[dev]
make validate     # config/, skills/, memory schema
make test         # 41 tests (verified 2026-09-29)
bash scripts/local-validate.sh   # validate + lint + tests, CI parity
```

Copy and fill the env template (never committed — `.gitignore:14-18`):

```bash
cp config/example.env .env
chmod 600 .env
# fill: HERMES_PRIMARY_API_KEY, HERMES_FALLBACK_API_KEY,
#       HERMES_TELEGRAM_BOT_TOKEN, HERMES_TELEGRAM_ALLOWED_CHAT_IDS,
#       BITRIX24_BASE_URL, BITRIX24_WEBHOOK_TOKEN
```

Required environment variables (exact names, from `config/example.env`):

| Variable | Consumer | Key reference |
|---|---|---|
| `HERMES_PRIMARY_API_KEY` | Mistral (primary) | `config/model-routing.yaml:17` |
| `HERMES_FALLBACK_API_KEY` | OVH AI (fallback) | `config/model-routing.yaml:26` |
| `HERMES_TELEGRAM_BOT_TOKEN` | Telegram gateway | `config/gateway/telegram.yaml:6` |
| `HERMES_TELEGRAM_ALLOWED_CHAT_IDS` | Telegram ACL | `config/gateway/telegram.yaml:14` |
| `HERMES_MEMORY_PATH` | sqlite memory store | `config/hermes.yaml:27` |
| `BITRIX24_BASE_URL` / `BITRIX24_WEBHOOK_TOKEN` | Bitrix24 skills | `skills/bitrix/crm-notify.md:24-26` |

**Production note (M6):** set `HERMES_MEMORY_PATH` to an absolute path on a
persistent volume, e.g. `/var/lib/hermes/hermes-memory.sqlite` — not the
repo-relative default.

## 3. LLM provider configuration

Endpoints and keys per provider (EU-only, `config/model-routing.yaml`):

```yaml
providers:
  - name: primary
    vendor: mistral          # https://api.mistral.ai/v1 — key: HERMES_PRIMARY_API_KEY
    model: mistral-large-2411     # pinned (H2 closed 2026-09-20); never *-latest
    context_length: 128000        # validator requires >= 64000 (main.py:104-121)
  - name: fallback
    vendor: ovh-ai           # OVH AI Endpoints (France) — key: HERMES_FALLBACK_API_KEY
    model: llama-3.1-70b-instruct
    context_length: 128000
```

Connectivity verification (minimal inference, once runtime is attached —
audit finding C1):

```bash
# primary
curl -sf https://api.mistral.ai/v1/chat/completions \
  -H "Authorization: Bearer $HERMES_PRIMARY_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"mistral-large-2411","messages":[{"role":"user","content":"reply ok"}],"max_tokens":8}'

# then repeat against the fallback endpoint with $HERMES_FALLBACK_API_KEY
```

Expected: HTTP 200 with a completion. On failure: capture the exact provider
error and file per `skills/infrastructure/incident-triage.md`.

## 4. Gateway activation (Telegram)

1. Create bot via @BotFather; store token in `HERMES_TELEGRAM_BOT_TOKEN`
   (env only — `config/gateway/telegram.yaml:6`).
2. Populate `HERMES_TELEGRAM_ALLOWED_CHAT_IDS` with the numeric chat IDs of
   the ops group. **Empty/unset = deny-all by contract**
   (`config/gateway/telegram.yaml:10-14`); never deploy an open bot.
3. Confirm `confirmation_required_above: medium` stays at or below `medium`
   (`config/gateway/telegram.yaml:16`).
4. Verify rate limit `per_minute: 20` (`:21-22`) and redaction patterns
   (`:24-29`) are intact.

## 5. Docker deployment (H3 — landed and build-verified)

The canonical artefacts live in the repository. This guide deliberately does
not reproduce them: duplicated snippets are exactly what fell out of sync when
H2 and H3 were remediated.

| Artefact | Path | Properties that matter at deploy time |
|---|---|---|
| Image | `Dockerfile` | `python:3.12-slim`; non-root `hermes` (uid 10001); `ENV HERMES_MEMORY_PATH=/var/lib/hermes/hermes-memory.sqlite`; healthcheck runs `python main.py validate`; `ENTRYPOINT ["hermes"]`; no secrets baked in |
| Runtime | `docker-compose.yml` | `read_only: true`, `tmpfs: /tmp`, `cap_drop: [ALL]`, `no-new-privileges:true`, limits `cpus 2.0 / memory 4g / pids 512`, `hermes-net` bridge with **no published ports**, `env_file: .env` |
| Build exclusions | `.dockerignore` | `.env`, `.env.*`, `config/*.local.yaml`, `runtime/`, `*.log`, VCS/IDE dirs, Python caches, `tests/`, `docs/`, `.github/`, `deploy/` |

Verify the artefacts before deploying — do not trust this table, re-run:

```bash
docker build -t jol-hermes .
docker compose config >/dev/null && echo "compose config OK"
docker run --rm --entrypoint id jol-hermes              # expect uid=10001(hermes)
docker run --rm --entrypoint python jol-hermes main.py validate
```

Deploy:

```bash
docker compose up -d --build
docker compose logs -f hermes
```

Destructive-sandbox test before go-live (mandate constraint): run
`rm -rf /tmp/should-not-exist-host` inside the container tool backend and
confirm host filesystem is untouched.

## 6. Systemd deployment (non-Docker — H3 landed)

Canonical unit: `deploy/hermes.service` → install to
`/etc/systemd/system/hermes.service`. Its own header states the
prerequisites: a dedicated unprivileged `hermes` user, a repo checkout at
`/opt/hermes` with `.venv` created via `make setup`, and secrets in
`/home/hermes/.hermes/.env` (chmod 600, owned `hermes:hermes`).

Sandboxing in force: `User/Group=hermes`, `NoNewPrivileges=true`,
`ProtectSystem=strict`, `ProtectHome=read-only`, `PrivateTmp=true`,
`ReadWritePaths=/var/lib/hermes /var/log/hermes`. Note the `-` prefix on
`EnvironmentFile`: the unit starts even when the env file is missing, so the
agent must fail fast on absent secrets rather than run unconfigured.

```bash
sudo install -m 0644 deploy/hermes.service /etc/systemd/system/hermes.service
sudo systemctl daemon-reload
sudo systemctl enable --now hermes
systemctl status hermes
```

Log rotation (M7): canonical config `deploy/logrotate-hermes` → install to
`/etc/logrotate.d/hermes`. It rotates `/var/log/hermes/*.log` `daily`,
`rotate 30`, `compress` with `delaycompress`, `missingok`, `notifempty`, and
recreates files as `0640 hermes:hermes` under `su hermes hermes`.

```bash
sudo install -m 0644 deploy/logrotate-hermes /etc/logrotate.d/hermes
sudo logrotate -d /etc/logrotate.d/hermes   # dry run, expect no errors
```

## 7. Smoke sequence (post-deploy, runtime-attached)

Run in order; stop on first failure:

1. `python main.py validate` on the deployed copy.
2. Provider connectivity calls (§3).
3. Low-risk skill end-to-end: trigger "morning report"
   (`skills/operations/morning-report.md`) via Telegram; confirm redacted,
   length-limited output and a write to memory namespace `ops.reports`.
4. ACL negative test: message from a chat ID **not** in the allowlist must
   be dropped silently (`docs/data-flow.md` rule 1).
5. Confirmation gate test: request `disk cleanup` — must produce a plan and
   wait for confirmation (`skills/operations/disk-cleanup.md` step 4).

## 8. Rollback procedure

Per `docs/runbooks/operating-hermes.md:28-33`:

1. Config/skill regression: `git revert <commit>`, redeploy (artefacts are
   pure files).
2. Bad memory writes: identify namespace, `hard_delete` purge, document in
   incident record.
3. Kill switch: stop the service (`systemctl stop hermes` /
   `docker compose down`); if remote stop fails, revoke the Telegram bot
   token at @BotFather.
