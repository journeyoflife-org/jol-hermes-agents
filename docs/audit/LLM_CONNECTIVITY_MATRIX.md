# LLM Connectivity Matrix — jol-hermes-agents

Audit date: 2026-08-13 · Source of truth: `config/model-routing.yaml`.

> **Honesty note (audit findings C1/C2):** this repository ships no runtime,
> so live connectivity (`hermes chat -q "reply ok" --no-tools`) could not be
> executed from here. Status below distinguishes *declared* configuration
> from *verified* connectivity. Context-window and tool-support values are
> vendor-documented facts for the named model families; they become binding
> only once re-verified against the pinned model IDs (H2) at deploy time.

## Matrix

| Provider | Model (as configured) | Context window | Tool / function-calling | Region | Status | Last verified |
|---|---|---|---|---|---|---|
| Mistral AI (primary) | `mistral-large-latest` (`config/model-routing.yaml:13`) | 128k (≥64k ✅) | Supported (function calling) | `eu` (Paris, FR) ✅ | **CONFIGURED — connectivity UNVERIFIED** (no runtime in repo, C1) | never (config-only audit) |
| OVH AI Endpoints (fallback) | `llama-3.1-70b-instruct` (`config/model-routing.yaml:21`) | 128k (≥64k ✅) | Supported via OpenAI-compatible tool API | `eu` (France) ✅ | **CONFIGURED — connectivity UNVERIFIED** | never (config-only audit) |

Both models clear the mandated 64,000-token minimum. Neither is pinned to a
versioned identifier (finding H2 — `-latest` aliases are mutable).

## Failover behaviour (declared)

```yaml
# config/model-routing.yaml:26-31
routing:
  strategy: failover             # primary -> fallback, in order
  fallback_on:
    - timeout
    - rate_limited
    - server_error
```

- Primary timeout: 60 s, 2 retries (`config/model-routing.yaml:15-16`).
- Fallback timeout: 90 s, 1 retry (`config/model-routing.yaml:23-24`).
- Chain exhaustion: `degrade_gracefully` → notify engineering within 30 min
  (`config/agent-policy.yaml:90-93`); runtime must additionally announce the
  degraded mode (`docs/architecture.md:56-57`).

**Failover test (mandate §3.5.7)**: blocked-primary simulation requires the
runtime; procedure defined in `CHECKLIST.md` gate P2-7.

## Config snippets per provider

Primary (Mistral):

```yaml
# config/model-routing.yaml:10-16
- name: primary
  vendor: mistral
  region: eu
  model: mistral-large-latest      # TODO(H2): pin dated model ID
  api_key_env: HERMES_PRIMARY_API_KEY
  timeout_s: 60
  max_retries: 2
```

Fallback (OVH AI):

```yaml
# config/model-routing.yaml:18-24
- name: fallback
  vendor: ovh-ai
  region: eu
  model: llama-3.1-70b-instruct
  api_key_env: HERMES_FALLBACK_API_KEY
  timeout_s: 90
  max_retries: 1
```

## Provider decision table (selection rationale)

| Criterion | Mistral (primary) | OVH AI (fallback) |
|---|---|---|
| EU data residency + DPA | yes (Paris) — required by `config/model-routing.yaml:4-5` | yes (France) |
| Context ≥ 64k | yes (128k) | yes (128k) |
| Tool calling | yes | yes (compat API) |
| Role | lowest-latency quality tier | capacity/outage fallback |
| Region CI check | passes `{eu, eu-central, eu-west}` (`main.py:37`) | passes |

## Verification procedure (to execute when runtime is attached)

```bash
# 1. Minimal inference, no tools — expected: successful short completion
hermes chat -q "reply ok" --no-tools

# 2. On failure: capture provider error verbatim
tail -n 50 logs/agent.log logs/errors.log

# 3. Direct API probe independent of the runtime
curl -sf https://api.mistral.ai/v1/chat/completions \
  -H "Authorization: Bearer $HERMES_PRIMARY_API_KEY" \
  -d '{"model":"<PINNED_MODEL>","messages":[{"role":"user","content":"reply ok"}],"max_tokens":8}'

# 4. Context-window re-verification against the pinned model
#    (provider /models endpoint or docs snapshot; record result in this table)
```

Update the *Status* and *Last verified* columns after each run; this file is
the durable record required by mandate Phase 4 item 4.
