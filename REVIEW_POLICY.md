# Code Review Policy — jol-hermes-agents

**Status:** ACTIVE (solo-operator phase, pre-deployment)  
**Last updated:** 2026-09-29  
**Next review:** When the first employee or contractor joins the project

---

## Context

This repository is currently maintained by a **sole owner/developer** (JourneyOfLife). Until the team grows, the standard CODEOWNERS-enforced separation of duties (author ≠ reviewer) cannot be fully implemented.

However, compliance obligations (GDPR accountability, SOC2 Type II intent, ISO 27001 A.14.2.2) require that changes are reviewed before merge. This policy documents how that intent is preserved during the solo-operator phase.

---

## Current process (solo-operator phase)

### 1. Automated gates are the primary control

Every change must pass **all** of the following before merge:

- `scripts/local-validate.sh` — config validation, lint (ruff + yamllint), secret scan, tests (41/41)
- `.pre-commit-config.yaml` — ruff, ruff-format, check-yaml, detect-private-key, gitleaks
- Manual verification: the author must empirically verify the change works (no "trust the code looks right")

**Evidence required:** The PR description must include the output of `local-validate.sh` showing all checks passed.

### 2. Mandatory cooling-off period

**PRs must remain open for at least 48 hours before merge.**

Rationale:
- Catches impulsive changes (e.g., "quick fix" that breaks something)
- Provides a window for the author to reconsider
- Creates an audit trail (PR open timestamp → merge timestamp)

**Exception:** Critical security fixes (e.g., leaked secret) may be merged immediately if documented with a `SECURITY` label and rationale.

### 2.1 Do later commits restart the cooling-off period?

The 48 hours run from the **later** of: the PR opening time, or the last *substantive* commit pushed to the branch.

**Substantive — restarts the clock:**

- Any change to code, scripts, or tests
- Any change to `config/`, `memory/`, or `prompts/` — in this repository these *are* agent behaviour, not documentation
- Any change to the dependency set (`pyproject.toml`, `uv.lock`)
- Any change that alters a declared control, autonomy level, data class, retention period, or approval requirement

**Non-substantive — does not restart the clock:**

- Typographical and wording corrections
- Citation fixes (paths, key names, line numbers) that do not change meaning
- Adding verification evidence for work already under review
- CHANGELOG entries describing commits already in the PR

**Two conditions apply to every commit pushed after review has begun:**

1. The author states the classification (substantive or not) in a PR comment at push time, and lists the files touched.
2. The reviewer reads the **final** diff, not the diff as it stood when review began. Merging against a superseded review is not a review.

**Why not a blanket rule in either direction:**

- A blanket *restart* deadlocks a sole operator: review finds a correction, the correction restarts 48 hours, the next review finds another. A PR under active review could never merge.
- A blanket *no restart* lets behaviour change after the review that approved it, which defeats the control entirely.

Classifying by risk preserves the control's actual intent — that the content being merged was genuinely considered — without creating a deadlock.

**Anti-abuse.** A commit that changes the *meaning* of a control is substantive however it is labelled; when in doubt, treat it as substantive. If a PR restarts the clock more than twice, the change was not ready for review — close it and reopen once the work is complete, rather than accumulating resets.

*Provenance: added 2026-09-29 after PR #14 received a documentation-only follow-up commit while under review and this policy had no answer.*

### 3. Self-review checklist

Before merging, the author must confirm (via PR comment or description) that they have reviewed:

- [ ] **Security:** No secrets committed, no `eval`/`exec`, no `shell=True`, YAML loaded safely
- [ ] **Compliance:** EU-only routing preserved (if config change), retention policy unchanged (or intentionally updated)
- [ ] **Testing:** New functionality covered by tests, existing tests still pass
- [ ] **Documentation:** CHANGELOG updated, audit docs updated if applicable
- [ ] **Deployment impact:** Does this change affect the runtime? If yes, has the runtime repo been updated?

### 4. Audit trail

Every merge must be traceable:
- PR number + link
- Author (commit signature)
- Verification evidence (local-validate.sh output)
- Merge timestamp (GitHub records this)

This satisfies the **intent** of separation of duties: the author is accountable, and the audit trail is complete.

---

## Transition trigger: when to restore full CODEOWNERS

**Re-enable required code-owner review when:**
1. The first employee or contractor joins the project, **or**
2. A second member is added to `@journeyoflife-org/security`, **or**
3. The project moves from "definition repo" to "runtime repo" (C1 resolved)

**Action:** Update the root `CODEOWNERS` — the only file GitHub reads, since `.github/CODEOWNERS` was removed under audit finding N1 — to require review, and remove the "solo-operator phase" note from both this document and the `CODEOWNERS` header comment.

---

## Admin bypass (emergency lane)

If the cooling-off period has passed and all gates are green, but a technical issue prevents merge (e.g., GitHub outage, ruleset misconfiguration), the repository admin may use the **admin bypass lane** granted by the `protect-main` ruleset.

**Conditions:**
- All automated gates are green
- Cooling-off period has passed (48 hours)
- Documented in the PR comments with rationale

**This is not a workaround for the review requirement** — it's a technical escape hatch for platform issues.

---

## Compliance mapping

| Control | How this policy satisfies it |
|---|---|
| **SOC2 Type II** (CC8.1 — Change management) | Changes are reviewed (self-review checklist), tested (automated gates), and documented (PR + audit trail) |
| **ISO 27001 A.14.2.2** (Secure development) | Automated security checks (gitleaks, ruff, secret scan), testing, and documentation |
| **GDPR Art. 32** (Security of processing) | EU-only routing enforced, retention policy validated, no secrets in code |
| **Separation of duties** | Acknowledged as not fully implementable in solo phase; compensated by cooling-off period + self-review checklist + audit trail |

---

## Review cadence

This policy must be reviewed:
- **Quarterly** (or when the team grows)
- **After any security incident**
- **When the first employee/contractor joins** (transition to full CODEOWNERS)

---

## Questions?

Contact: `@journeyoflife-org/security` (currently sole member: JourneyOfLife)
