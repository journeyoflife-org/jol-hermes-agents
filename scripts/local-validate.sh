#!/usr/bin/env bash
# Run the same validation chain as CI, locally.
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PY:-.venv/bin/python}"
[[ -x "$PY" ]] || PY="$(command -v python3)"

echo "==> validate (config, skills, memory)"
"$PY" main.py validate

echo "==> lint"
bash scripts/lint.sh

echo "==> tests"
"$PY" -m pytest

echo "local-validate: all checks passed"
