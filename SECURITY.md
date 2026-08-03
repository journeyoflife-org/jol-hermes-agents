# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.x     | yes       |

## Reporting a vulnerability

**Do not open a public issue for security problems.**

Email: `security@jol.example` (replace with the real security contact).

- Include a description, reproduction steps, and affected component
  (config, skill, gateway, memory).
- You will receive an acknowledgement within 2 working days and a
  remediation plan within 7 days.
- Do not access or exfiltrate data beyond what is needed to demonstrate
  the issue.

## Scope specific to this agent

- Prompt-injection vectors in skills, prompts, or gateway messages.
- Any configuration change that routes LLM traffic outside the EU.
- Secrets committed to the repository (see CI secret scan).
- Memory writes bypassing `memory/schema.yaml` or retention policy.

## Hardening baseline

- EU-only LLM provider chain enforced in `config/model-routing.yaml`.
- Secrets are supplied via environment variables only (`config/example.env`).
- Every push is scanned for secrets (open-source gitleaks CLI in CI) and
  analysed with CodeQL.
