#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
.venv/bin/ruff check signaldesk tests
.venv/bin/pytest
node --check signaldesk/static/app.js
.venv/bin/signaldesk-benchmark --output runs/verification
