#!/usr/bin/env bash
# Lint: Python (ruff) + YAML (yamllint) + secret patterns.
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PY:-.venv/bin/python}"
[[ -x "$PY" ]] || PY="$(command -v python3)"

echo "==> ruff"
"$PY" -m ruff check .

echo "==> yamllint"
"$PY" -m yamllint -c .yamllint config/ memory/

echo "==> naive secret scan (tracked files)"
# CI uses gitleaks; this is a fast local approximation.
if git grep -nIE \
  "(api[_-]?key|secret|token|password)[\"']?\s*[:=]\s*[\"'][A-Za-z0-9_\-]{16,}" \
  -- ':!config/example.env' ':!scripts/*' ':!tests/*' ':!.github/*'; then
  echo "possible hardcoded secret found" >&2
  exit 1
fi

echo "lint: OK"
