# Deployment Guide — jol-hermes-agents

Status: **proposed runbook** (audit finding H3 — no packaging artefacts exist
in the repo yet; templates below are ready to land as files). This guide
covers the declarative repo plus the runtime boundary described in
`AUDIT_REPORT.md` (C1).

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
make test         # 27 tests
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
| `HERMES_PRIMARY_API_KEY` | Mistral (primary) | `config/model-routing.yaml:14` |
| `HERMES_FALLBACK_API_KEY` | OVH AI (fallback) | `config/model-routing.yaml:22` |
| `HERMES_TELEGRAM_BOT_TOKEN` | Telegram gateway | `config/gateway/telegram.yaml:6` |
| `HERMES_TELEGRAM_ALLOWED_CHAT_IDS` | Telegram ACL | `config/gateway/telegram.yaml:10` |
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
    model: mistral-large-latest   # FIX H2: pin a dated model ID
  - name: fallback
    vendor: ovh-ai           # OVH AI Endpoints (France) — key: HERMES_FALLBACK_API_KEY
    model: llama-3.1-70b-instruct
```

Connectivity verification (minimal inference, once runtime is attached —
audit finding C1):

```bash
# primary
curl -sf https://api.mistral.ai/v1/chat/completions \
  -H "Authorization: Bearer $HERMES_PRIMARY_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"<PINNED_PRIMARY_MODEL>","messages":[{"role":"user","content":"reply ok"}],"max_tokens":8}'

# then repeat against the fallback endpoint with $HERMES_FALLBACK_API_KEY
```

Expected: HTTP 200 with a completion. On failure: capture the exact provider
error and file per `skills/infrastructure/incident-triage.md`.

## 4. Gateway activation (Telegram)

1. Create bot via @BotFather; store token in `HERMES_TELEGRAM_BOT_TOKEN`
   (env only — `config/gateway/telegram.yaml:6`).
2. Populate `HERMES_TELEGRAM_ALLOWED_CHAT_IDS` with the numeric chat IDs of
   the ops group. **Empty/unset = deny-all by contract**
   (`config/gateway/telegram.yaml:9`); never deploy an open bot.
3. Confirm `confirmation_required_above: medium` stays at or below `medium`
   (`config/gateway/telegram.yaml:12`).
4. Verify rate limit `per_minute: 20` (`:18`) and redaction patterns
   (`:20-25`) are intact.

## 5. Docker deployment (proposed — lands H3)

Proposed `Dockerfile` (to be added to repo root):

```dockerfile
FROM python:3.12-slim AS runtime
RUN useradd --create-home --uid 10001 hermes
WORKDIR /app
COPY pyproject.toml README.md main.py ./
COPY config skills memory prompts context ./
RUN pip install --no-cache-dir .
USER hermes
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
  CMD python main.py validate || exit 1
ENTRYPOINT ["hermes"]
```

Proposed `docker-compose.yml`:

```yaml
services:
  hermes:
    build: .
    restart: unless-stopped
    env_file: .env                    # never hardcode; chmod 600
    volumes:
      - hermes-state:/var/lib/hermes  # persistent memory/store
    read_only: true
    tmpfs: [/tmp]
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    networks: [hermes-net]            # custom bridge, no published ports
    deploy:
      resources:
        limits: { cpus: "2.0", memory: 4g, pids: 512 }

volumes:
  hermes-state:

networks:
  hermes-net:
    internal: false                   # egress needed for LLM APIs/Telegram
```

Proposed `.dockerignore`: `.env`, `.env.*`, `runtime/`, `*.log`, `.venv/`,
`.git/`, `tests/`.

Deploy:

```bash
docker compose up -d --build
docker compose logs -f hermes
```

Destructive-sandbox test before go-live (mandate constraint): run
`rm -rf /tmp/should-not-exist-host` inside the container tool backend and
confirm host filesystem is untouched.

## 6. Systemd deployment (non-Docker, proposed)

Proposed `/etc/systemd/system/hermes.service`:

```ini
[Unit]
Description=Hermes JOL operations agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=hermes
Group=hermes
EnvironmentFile=-/home/hermes/.hermes/.env   # chmod 600, owned hermes:hermes
WorkingDirectory=/opt/hermes
ExecStart=/opt/hermes/.venv/bin/hermes
Restart=on-failure
RestartSec=5
StandardOutput=append:/var/log/hermes/agent.log
StandardError=append:/var/log/hermes/errors.log
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/var/lib/hermes /var/log/hermes

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hermes
systemctl status hermes
```

Log rotation (M7): `/etc/logrotate.d/hermes` with `daily`, `rotate 30`,
`compress`, `missingok` on `/var/log/hermes/*.log`.

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
