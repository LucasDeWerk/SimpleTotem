#!/usr/bin/env bash
# Wrapper SiTef — detecta frozen binary ou source tree.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/SimpleTotem-backend"

if [ -f "$BACKEND" ] && [ -x "$BACKEND" ] && [ ! -d "$BACKEND" ]; then
  # Frozen binary PyInstaller — passa flag de modo worker
  exec "$BACKEND" --sitef-worker
else
  # Dev: source tree com virtualenv
  PYTHON="python3"
  if [ -x "$BACKEND/.venv/bin/python3" ]; then
    PYTHON="$BACKEND/.venv/bin/python3"
  fi
  exec "$PYTHON" "$BACKEND/services/sitef_worker.py"
fi
