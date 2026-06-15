#!/usr/bin/env bash
# Wrapper fixo para o sitef_worker — usado com sudo NOPASSWD no totem.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/SimpleTotem-backend"
PYTHON="python3"

if [ -x "$BACKEND/.venv/bin/python3" ]; then
  PYTHON="$BACKEND/.venv/bin/python3"
fi

exec "$PYTHON" "$BACKEND/services/sitef_worker.py"
