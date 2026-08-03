# Runbook — operating Hermes

## Deploy a config/skill change

1. Open PR; CI (validate + lint + tests + secret scan) must be green.
2. CODEOWNER review for `config/`, `memory/`, `agent-policy.yaml`.
3. Merge → agent reloads declarative artefacts on next cycle.
4. Verify: `python main.py validate` on the deployed copy; trigger a
   low-risk skill (e.g. "morning report") and check output.

## Rotate secrets

Secrets live only in the environment (`.env` / secret manager), never in
the repo.

1. Issue new credential at the vendor (LLM provider / Telegram / Bitrix24).
2. Update the secret store; restart the agent process.
3. Verify with `scripts/smoke-test.sh` and one live skill invocation.
4. Revoke the old credential at the vendor.

## Kill switch (stop the agent immediately)

1. Stop the agent process / disable the systemd unit.
2. If remote stop is impossible: revoke the Telegram bot token — the
   gateway becomes unreachable.
3. Announce in the ops channel; create a Bitrix24 task for follow-up.

## Rollback a behaviour change

- Config/skill: revert the offending commit, redeploy (artefacts are pure
  files — rollback is a git revert).
- Bad memory writes: identify the namespace, purge via retention tooling
  (`hard_delete`), document in the incident record.

## Suspected prompt injection

1. Kill switch (above).
2. Preserve evidence: gateway logs, the offending message, audit trail.
3. Triage via `skills/infrastructure/incident-triage.md`; treat as SEV2
   minimum if any mutation occurred.
4. Fix: tighten skill constraints or ACL, add regression test, redeploy.
