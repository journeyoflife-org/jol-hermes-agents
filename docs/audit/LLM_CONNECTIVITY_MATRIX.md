# LLM Connectivity Matrix — jol-hermes-agents

Audit date: 2026-08-13 · Amended: 2026-09-29 · Source of truth: `config/model-routing.yaml`.

> **Amendment (2026-09-29).** The 2026-08-13 snapshot recorded the primary
> model as `mistral-large-latest`. Finding **H2 was remediated on 2026-09-20**
> (commit `6646790`, PR #8): the primary is now pinned to
> `mistral-large-2411`, both providers declare `context_length: 128000`, and
> `check_provider_models` (`main.py:104-121`) rejects `*-latest` aliases and
> context windows below 64 000 tokens. This file was not updated at the time
> and contradicted the remediation table at `AUDIT_REPORT.md:239`. Corrected
> here: the current-state cells, the `file:line` references and the config
> snippets. The original snapshot is preserved in git history and is not
> restated as current. Connectivity remains **unverified** (C1 — no runtime).

> **Honesty note (audit findings C1/C2):** this repository ships no runtime,
> so live connectivity (`hermes chat -q "reply ok" --no-tools`) could not be
> executed from here. Status below distinguishes *declared* configuration
> from *verified* connectivity. Context-window and tool-support values are
> vendor-documented facts for the named model families; they become binding
> only once re-verified against the pinned model IDs at deploy time.

## Matrix

| Provider | Model (as configured) | Context window | Tool / function-calling | Region | Status | Last verified |
|---|---|---|---|---|---|---|
| Mistral AI (primary) | `mistral-large-2411` — pinned (`config/model-routing.yaml:15`) | 128k declared (`context_length`, ≥64k ✅) | Supported (function calling) | `eu` (Paris, FR) ✅ | **CONFIGURED — connectivity UNVERIFIED** (no runtime in repo, C1) | never (config-only audit) |
| OVH AI Endpoints (fallback) | `llama-3.1-70b-instruct` (`config/model-routing.yaml:24`) | 128k declared (`context_length`, ≥64k ✅) | Supported via OpenAI-compatible tool API | `eu` (France) ✅ | **CONFIGURED — connectivity UNVERIFIED** | never (config-only audit) |

Both models clear the mandated 64,000-token minimum and both are pinned to
versioned identifiers (finding **H2 — closed**; `*-latest` aliases are mutable
and are now rejected by the validator, `main.py:104-121`). Re-pinning after a
new model release is a deliberate act, never an automatic one
(`config/model-routing.yaml:13-14`).

## Failover behaviour (declared)

```yaml
# config/model-routing.yaml:30-35
routing:
  strategy: failover             # primary -> fallback, in order
  fallback_on:
    - timeout
    - rate_limited
    - server_error
```

- Primary timeout: 60 s, 2 retries (`config/model-routing.yaml:18-19`).
- Fallback timeout: 90 s, 1 retry (`config/model-routing.yaml:27-28`).
- Chain exhaustion: `degrade_gracefully` → notify engineering within 30 min
  (`config/agent-policy.yaml` → `escalation.rules`,
  `provider_chain_exhausted`); runtime must additionally announce the
  degraded mode (`docs/architecture.md:56-57`).

**Failover test (mandate §3.5.7)**: blocked-primary simulation requires the
runtime; procedure defined in `CHECKLIST.md` gate P2-7.

## Config snippets per provider

Primary (Mistral):

```yaml
# config/model-routing.yaml:10-19
- name: primary
  vendor: mistral
  region: eu
  model: mistral-large-2411        # pinned — H2 closed 2026-09-20
  context_length: 128000           # validator requires >= 64000
  api_key_env: HERMES_PRIMARY_API_KEY
  timeout_s: 60
  max_retries: 2
```

Fallback (OVH AI):

```yaml
# config/model-routing.yaml:21-28
- name: fallback
  vendor: ovh-ai
  region: eu
  model: llama-3.1-70b-instruct
  context_length: 128000           # validator requires >= 64000
  api_key_env: HERMES_FALLBACK_API_KEY
  timeout_s: 90
  max_retries: 1
```

## Provider decision table (selection rationale)

| Criterion | Mistral (primary) | OVH AI (fallback) |
|---|---|---|
| EU data residency + DPA | yes (Paris) — required by `config/model-routing.yaml:4-5` | yes (France) |
| Context ≥ 64k | yes (128k declared, CI-enforced) | yes (128k declared, CI-enforced) |
| Tool calling | yes | yes (compat API) |
| Role | lowest-latency quality tier | capacity/outage fallback |
| Region CI check | passes `{eu, eu-central, eu-west}` (`main.py:52`, enforced at `main.py:130-136`) | passes |

## Verification procedure (to execute when runtime is attached)

```bash
# 1. Minimal inference, no tools — expected: successful short completion
hermes chat -q "reply ok" --no-tools

# 2. On failure: capture provider error verbatim
tail -n 50 logs/agent.log logs/errors.log

# 3. Direct API probe independent of the runtime
curl -sf https://api.mistral.ai/v1/chat/completions \
  -H "Authorization: Bearer $HERMES_PRIMARY_API_KEY" \
  -d '{"model":"mistral-large-2411","messages":[{"role":"user","content":"reply ok"}],"max_tokens":8}'

# 4. Context-window re-verification against the pinned model
#    (provider /models endpoint or docs snapshot; record result in this table)
```

Update the *Status* and *Last verified* columns after each run; this file is
the durable record required by mandate Phase 4 item 4.
