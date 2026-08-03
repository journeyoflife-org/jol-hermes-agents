#!/usr/bin/env bash
# Smoke test: the repository must be self-consistent and runnable.
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PY:-.venv/bin/python}"
[[ -x "$PY" ]] || PY="$(command -v python3)"

echo "==> entrypoint help"
"$PY" main.py | head -n 5

echo "==> full validation"
"$PY" main.py validate

echo "==> skill inventory"
find skills -name '*.md' | sort

echo "smoke-test: OK"
