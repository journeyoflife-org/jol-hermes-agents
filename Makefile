PY ?= .venv/bin/python
PIP ?= .venv/bin/pip

.PHONY: setup validate lint test smoke clean

setup:
	python3 -m venv .venv || true
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

validate:
	$(PY) main.py validate

lint:
	$(PY) -m ruff check .
	$(PY) -m yamllint -c .yamllint config/ memory/ || true

test:
	$(PY) -m pytest

smoke:
	bash scripts/smoke-test.sh

clean:
	rm -rf .pytest_cache .ruff_cache **/__pycache__
