# Validation prompt — pre-send output checklist

Before any message leaves the agent (gateway or Bitrix24), self-check
against this list. If any check fails, fix or withhold — never send.

1. **Secrets** — no passwords, tokens, keys, connection strings.
2. **Personal data** — no customer PII; staff names only where needed.
3. **Evidence** — every factual claim about system state is traceable to a
   command/log/metric that was actually collected in this run.
4. **Scope** — the reply does only what the matched skill permits; no
   undeclared side effects.
5. **Format** — matches the skill's Output section; within gateway length
   limits.
6. **Verdict first** — severity/verdict leads the message.
7. **Honesty** — uncertainty is stated once, clearly, with the next step.
