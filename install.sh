#!/usr/bin/env bash
# Idempotent bootstrap for the jol-hermes-agents validator (audit finding I6).
# Safe to re-run; fails fast with clear messages on unmet prerequisites.
set -euo pipefail
cd "$(dirname "$0")"

MIN_PY="3.12"

die() { echo "install: ERROR: $*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || die "python3 not found in PATH"

PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if ! python3 - "$MIN_PY" "$PY_VER" <<'PY'
import sys
minimum = tuple(map(int, sys.argv[1].split(".")))
current = tuple(map(int, sys.argv[2].split(".")))
sys.exit(0 if current >= minimum else 1)
PY
then
  die "Python >= ${MIN_PY} required, found ${PY_VER}"
fi

if [[ ! -x .venv/bin/python ]]; then
  echo "install: creating .venv"
  python3 -m venv .venv
fi

echo "install: installing dependencies"
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -e ".[dev]"

echo "install: validating declarative artefacts"
.venv/bin/python main.py validate

echo "install: OK"
