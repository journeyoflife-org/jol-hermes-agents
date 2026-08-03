---
id: bitrix.crm-notify
name: Bitrix24 CRM notification
description: Push structured notifications into Bitrix24 CRM (chat messages / CRM items).
domain: bitrix
risk_level: low
owner: ops
---

# Bitrix24 CRM notification

## Purpose

Notify the team inside Bitrix24 where they already work: chat messages for
operational events, CRM-item comments for customer-related events.

## When to run

- Called by other skills (incident SEV1/2, compliance findings).
- On demand: "notify bitrix …".

## Steps

1. Resolve credentials from env: `BITRIX24_BASE_URL`,
   `BITRIX24_WEBHOOK_TOKEN` (see `config/example.env`). Fail fast and
   visibly if unset — never fall back to hardcoded values.
2. Map event → target:
   - operational event → ops group chat message.
   - customer-related event → comment on the matching CRM entity; if no
     entity matches, send to ops chat instead (do not create entities).
3. Render the message: title, severity/source skill, one-paragraph body,
   link back to source (incident id / scan run).
4. Send via the Bitrix24 webhook API; retry once on 5xx/timeout.
5. Log delivery metadata (timestamp, target id, status) to memory namespace
   `bitrix.notifications`. Never log message bodies containing personal
   data.

## Constraints

- Rate limiting: max 10 notifications per 10 minutes per target; batch or
  drop with a counter beyond that.
- Message bodies are redacted per the same rules as the Telegram gateway.

## Output

Delivery confirmation (`sent | target | message id`) or explicit failure
with reason.
