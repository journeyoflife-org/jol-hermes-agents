## What & why

<!-- One paragraph: what changes and why it is safe. -->

## Blast radius

<!-- Which agent behaviour can this change? Config / skill / memory / prompts. -->

## Validation

- [ ] `make validate lint test` passes locally
- [ ] `scripts/smoke-test.sh` run (attach output for prompt/config changes)
- [ ] No new secrets introduced (env-var references only)
- [ ] EU-only routing preserved (for `config/model-routing.yaml` changes)
- [ ] Retention coverage preserved (for `memory/` changes)
