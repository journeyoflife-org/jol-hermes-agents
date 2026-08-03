# Operational prompt — scheduled morning run

Used when Hermes is triggered by the scheduler (not a human message).

## Instructions

Produce today's morning report by executing `operations/morning-report.md`
exactly as written. Additional constraints for scheduled runs:

- No interactive questions: if a data source is unavailable, mark the
  section "UNAVAILABLE (source)" and continue; never fabricate values.
- Tone is factual and terse; the audience reads this before their coffee.
- If the overall verdict is not OK, the first line of the message must be
  the verdict, before any detail.
- Deliver via the configured gateway and store the digest in
  `ops.reports` per retention policy.
