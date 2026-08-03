#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -e '.[dev]'

if [[ "${1:-}" == "--demo" ]]; then
  export SIGNALDESK_DEMO=1
fi

exec .venv/bin/signaldesk
