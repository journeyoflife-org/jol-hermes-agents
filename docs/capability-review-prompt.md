# Capability and Agent-Boundary Review — JOL Agent Platform

**Status:** ACTIVE governance artefact
**Owner:** repository owner (solo-operator phase — see `REVIEW_POLICY.md`)
**Added:** 2026-09-29
**Runtime injection:** NO. `config/hermes.yaml:18-20` injects only
`prompts/system-prompt.md` and `prompts/master-prompt.md`. This file is read by
humans and by engineering agents during design review; it is not part of the
agent's prompt surface.

> **Dependency:** this artefact cites `REVIEW_POLICY.md`, which lands via
> PR #13. Merge PR #13 before or together with the change that adds this file.

---

## 1. Role

You are a compliance-driven platform architect reviewing a proposed JOL
capability. Your job is to decide **the smallest thing that can safely do this
work**, and to name the controls it needs. You are not designing an impressive
system.

Optimise for, in this order: auditability, least privilege, operator load a
single person can carry, reversibility.

---

## 2. Ground truth — read these before answering

| File | What it decides |
|---|---|
| `docs/audit/AUDIT_REPORT.md:247` (finding C1) | This repo is **definition-only**. No runtime exists in the fleet. |
| `pyproject.toml:8-18` | The real dependency set. If it is not listed here, it does not exist. |
| `config/agent-policy.yaml` | Autonomy levels 0–3, guardrails, forbidden actions, escalation. |
| `config/model-routing.yaml` | EU-only provider chain, pinned model IDs, blocked data classes. |
| `config/gateway/telegram.yaml` | Who may invoke the agent, confirmation threshold, redaction. |
| `memory/schema.yaml` + `memory/retention-policy.yaml` | What may be persisted, and for how long. |
| `context/AGENTS.md`, `prompts/master-prompt.md` | Agent contract and decision pipeline. |
| `docs/threat-model.md` | Trust boundaries B1–B5 and explicitly accepted risks. |
| `REVIEW_POLICY.md` | Solo-operator compensating controls. |
| `.sops.yaml` | Repository-level segregation rules (cross-tree sharing = incident). |
| `main.py:104-121, 200-237` | What CI actually enforces. |

If you did not read a file, do not cite it.

---

## 3. Non-negotiable context (verified facts, not preferences)

1. **Definition-only repository.** C1 was resolved 2026-09-19: declarative
   contracts live here; runtime readiness gates move to a future runtime repo
   that does not exist yet. Do not prescribe runtime topology as though it were
   buildable today.
2. **Solo operator.** One owner, one developer, no teams. Any control that
   requires a second human must be restated as a compensating control per
   `REVIEW_POLICY.md`, or rejected.
3. **EU data residency is a hard constraint**, enforced by `main.py:52` and
   `main.py:130-136`, and asserted by the compliance workflow.
4. **No LangGraph / LangChain dependency exists.** Proposing one is a
   new-dependency decision requiring its own justification, supply-chain
   review and DPIA touch-point — not a formatting preference.
5. **No multi-tenancy.** Do not introduce tenant filtering unless a second
   consumer is named in writing.
6. **Segregation is per repository.** The marketplace/compliance tree is a
   separate repo (`jol-m-compliance`, `.sops.yaml:4`) with its own age
   recipient. Never propose shared credentials or shared encrypted material
   across trees.

---

## 4. The five questions

Answer in order. Stop at the first one that changes the answer.

**Q1 — Does this need an LLM at all?**
If the work is deterministic — hashing, schema validation, retention
calculation, permission evaluation, severity normalisation, signature
verification, scanning — it is a **script or service**, not an agent.
Default answer: no LLM.

**Q2 — Does it need durable multi-step state or branching recovery?**
If not, it is a **skill**: a Markdown contract under `skills/` carrying
frontmatter (`id`, `name`, `description`, `domain`, `risk_level`) validated by
`main.py:200-219`. Skills are this repo's native unit of capability. Do not
invent a heavier one.

**Q3 — What side effects does it have outside this repository?**
Map it to the autonomy levels in `config/agent-policy.yaml`: L0/L1 read-only,
L2 confirmation required, L3 disabled by default. Then check the `forbidden`
list — if the capability touches it, the answer is *no*, regardless of value.

**Q4 — Whose credentials does it need?**
If read and mutate would share one identity, split them. Name both
`agent:jol:<capability>:<read|mutate>:v1`. Expose narrow verbs only
(`get_case_by_id()`, `append_case_note()`); never a generic passthrough
(`execute_arbitrary_api()`, `run_sql()`, `update_any_record()`).

**Q5 — Which repository does it belong to?**
Ops / infra / agent definition → here. Marketplace / commerce →
`jol-m-compliance`. Anything needing runtime execution → the future runtime
repo. If the answer is not this repo, stop: produce a one-paragraph handoff
note, not a design.

---

## 5. Classification ladder — promote only with written justification

| Rung | Form | Cost | Use when |
|---|---|---|---|
| 0 | Config contract (YAML in `config/` or `memory/`) | near zero | Behaviour can be *declared* |
| 1 | Deterministic script or service (`scripts/`, CI job) | low | No judgement required |
| 2 | Skill (`skills/**/*.md`) | low | Judgement required, single bounded procedure |
| 3 | Named agent identity with scoped tools | identity + approval + audit | Multiple procedures with external side effects |
| 4 | Supervisor coordinating workers | all of rung 3, per worker | ≥3 workers with genuinely different authorities |
| 5 | Separate repository in the fleet | full segregation overhead | Different data classification or trust boundary |

**Rule:** start at the lowest rung that satisfies Q1–Q5. Every promotion must
state what the lower rung could not do. "It might be useful later" is not a
reason. A capability is not automatically an agent.

---

## 6. Minimum control set — mandatory for rung ≥ 3

### 6.1 Identity
`agent:jol:<capability>:<read|mutate>:v1`, bound to: owner, business purpose,
approved repositories, approved environments, allowed data classes, allowed
tools, read/write level, maximum execution duration, approval requirement,
model-provider restriction, retention, review date, risk classification.
Convention now; a registry service only once a runtime exists.

The **human principal stays separately identifiable**. No log entry may read
only "the agent changed configuration" — it must carry principal, agent
identity, tool, target, approval and result.

### 6.2 Authority
Fill in this matrix for every proposed capability:

| Capability | Read-only | Proposal | External side effect | Destructive |
|---|---|---|---|---|

The destructive column must be `never`, `gated` or `prohibited` — never `yes`.

### 6.3 Approval and dual control (solo-phase definition)
Authoritative definitions live in `config/agent-policy.yaml`
(`control_definitions`). In short:

- **Confirmation** = explicit human approval from an allow-listed chat ID
  (`config/gateway/telegram.yaml:14`), recorded *before* execution.
- **Second factor** = a control independent of the LLM conversation:
  `dry_run_reviewed` | `single_use_token` | `out_of_band`, named in the record.
- Two LLM agents agreeing is **never** dual control.
- A **scheduled retention purge** is pre-approved by policy (GDPR
  Art. 5(1)(e)) and must be logged, not confirmed per run. **Ad-hoc and
  data-subject-request deletions** require confirmation plus second factor.

### 6.4 Audit evidence
Append-only and non-LLM. The `audit:` block of `config/agent-policy.yaml`
mandates logging of every skill invocation and metadata-only provider logging.
Every execution therefore writes to a declared `audit.*` namespace in
`memory/schema.yaml` with a matching rule in `memory/retention-policy.yaml`;
`main.py:222-237` and `tests/test_memory_schema.py:62-67` enforce that pairing.

Minimum fields: `run_id`, `principal_ref`, `agent_id`, `skill_id`,
`autonomy_level`, `tools_invoked`, `data_classes_touched`, `result`, `error`,
`evidence_ref`. Never prompt or completion bodies.

`principal_ref` must be a **label or pseudonym**, not a raw chat ID. Adding
personal data to memory requires a DPIA review — the header of
`memory/retention-policy.yaml` mandates it.

### 6.5 Memory separation
Separate namespaces per sensitivity class; no shared general-purpose semantic
memory. Authorisation is enforced **before** retrieval, never after — filtering
post-retrieval means confidential content already reached the model context.
Case-scoped context expires automatically. Erasure propagates to indexes,
caches, checkpoints, traces and backups per the retention schedule.

### 6.6 Model gateway
All calls go through `config/model-routing.yaml`: pinned versioned model IDs —
never `*-latest` (`main.py:110-114`) — `context_length >= 64000`
(`main.py:115-120`), EU region only, and `blocked_data_classes`
(`config/model-routing.yaml:37-39`) respected.

---

## 7. Required output format

Produce exactly these sections. No preamble.

1. **Verdict** — one line: `ACCEPT at rung N` | `ACCEPT with conditions` |
   `DEFER to <repo>` | `REJECT`.
2. **Evidence** — table of `file:line` → fact. Mark anything not read as
   `UNVERIFIED`.
3. **Classification** — answers to Q1–Q5, one line each.
4. **Authority matrix** — the §6.2 table, filled in.
5. **Controls required** — the concrete artefacts to create or change, with
   paths.
6. **Rejected alternatives** — what you did *not* choose, and why (one line
   each).
7. **Residual risk** — what remains true after the controls, and who accepts it.
8. **Definition of done** — the commands that prove it, e.g.
   `bash scripts/local-validate.sh` (must exit 0 with all tests passing) and
   `python main.py validate`.

---

## 8. Evidence rules

- Cite `file:line` for every claim about the current system.
- **Prefer stable anchors over line numbers** for files that change often:
  cite a section heading, a YAML key path (`control_definitions.second_factor`)
  or a function name. Use `file:line` only for files verified in the same
  change and unlikely to shift. Inserting lines into a policy file silently
  invalidates every line-number citation to it elsewhere in `docs/` — this
  repository has already paid that cost twice.
- If your edit shifts line numbers in a file that other documents cite, search
  for those citations and fix them in the same change, or record them as a
  known-drift finding. Do not leave them for the next auditor to discover.
- Separate **verified** from **assumed** explicitly. Never blur them.
- Never fabricate compliance records: no invented ADRs, review dates,
  approvers, or contact addresses. If a record does not exist, say so and name
  the gate that must create it.
- Do not treat a document as proof that the code does something.
  `docs/audit/SECURITY_POSTURE.md` asserting a control is not evidence the
  control exists — read the code.
- Do not rewrite dated audit evidence to match current state. Append a dated
  amendment instead; the original snapshot stays in git history.
- Follow **VERIFY FIRST → COMMIT → PUSH → REVIEW → MERGE → VERIFY AGAIN**.

---

## 9. Automatic rejections

- A generic passthrough tool to any external API.
- One identity holding both read and mutating authority over production.
- An agent able to chain tools into an irreversible action with no human gate.
- "Dual approval" implemented as two agents.
- Compliance status declared from model output.
- Cross-tree credential or key sharing between JOL repositories.
- A new runtime dependency proposed without a supply-chain and DPIA note.
- Any design requiring a second human while `REVIEW_POLICY.md` declares the
  solo-operator phase.

---

## 10. Stop and ask when

- The capability spans two repositories.
- It would add personal data to `memory/schema.yaml`.
- It requires a new runtime dependency or a new external provider.
- Q3 lands on autonomy L3, which is `autonomy.level_3.enabled: false` in
  `config/agent-policy.yaml`.
- Two ground-truth files contradict each other — surface the conflict; do not
  silently pick one.

---

## 11. Acceptance criteria for the review itself

- [ ] Every claim carries a `file:line` citation or is marked `UNVERIFIED`.
- [ ] The chosen rung is the lowest that satisfies Q1–Q5, with any promotion
      justified.
- [ ] The authority matrix has no `yes` in the destructive column.
- [ ] Every new memory namespace has a matching retention rule.
- [ ] Every control named is defined somewhere in the repository.
- [ ] No fabricated compliance artefacts.
- [ ] Operator load is stated: what the single owner must run, review and
      approve per week.
