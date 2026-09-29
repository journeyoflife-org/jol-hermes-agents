PY ?= .venv/bin/python
PIP ?= .venv/bin/pip

.PHONY: setup validate lint test smoke hooks hooks-install clean

setup:
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

validate:
	$(PY) main.py validate

lint:
	$(PY) -m ruff check .
	$(PY) -m yamllint -c .yamllint config/ memory/

test:
	$(PY) -m pytest

smoke:
	bash scripts/smoke-test.sh

# .pre-commit-config.yaml is a declared merge gate, so it must be runnable.
# `make hooks-install` wires it into .git/hooks once per clone; `make hooks`
# runs every hook against every file on demand (CI parity locally).
hooks:
	$(PY) -m pre_commit run --all-files

hooks-install:
	$(PY) -m pre_commit install

clean:
	rm -rf .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -not -path "./.venv/*" -exec rm -rf {} +
