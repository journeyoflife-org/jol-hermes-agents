# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.x     | yes       |

## Reporting a vulnerability

**Do not open a public issue for security problems.**

Preferred channel — GitHub private vulnerability reporting:

1. Go to <https://github.com/journeyoflife-org/jol-hermes-agents/security/advisories>
2. Choose **Report a vulnerability** (draft advisory, visible only to repo
   admins and the `@journeyoflife-org/security` team).

> Org admins: private vulnerability reporting must be enabled under
> Settings → Code security for the link above to accept reports
> (status unverified as of the 2026-09-29 audit — finding M3).

Fallback until a real mailbox is published: contact the
`@journeyoflife-org/security` team via the org's internal channels.
(`security@jol.example` is a placeholder — do NOT use it.)

- Include a description, reproduction steps, and affected component
  (config, skill, gateway, memory).
- You will receive an acknowledgement within 2 working days and a
  remediation plan within 7 days.
- Do not access or exfiltrate data beyond what is needed to demonstrate
  the issue.

## Scope specific to this agent

- Prompt-injection vectors in skills, prompts, or gateway messages.
- Any configuration change that routes LLM traffic outside the EU.
- Secrets committed to the repository (how scanning actually runs: see
  Hardening baseline below).
- Memory writes bypassing `memory/schema.yaml` or retention policy.

## Hardening baseline

- EU-only LLM provider chain enforced in `config/model-routing.yaml`.
- Secrets are supplied via environment variables only (`config/example.env`).
- Secret scanning and static analysis do **not** run automatically. Since
  2026-09-29 the CI workflows are manual-only (`workflow_dispatch`) to stay
  within the GitHub Actions minute budget. Run them on demand:
  `gh workflow run ci.yaml` (gitleaks) and `gh workflow run codeql.yml`.
- The gate that does run before merge is local: `scripts/local-validate.sh`
  (config validation, ruff, yamllint, a secret scan over tracked files, and
  the test suite). `.pre-commit-config.yaml` additionally defines a gitleaks
  hook for contributors who install it.
