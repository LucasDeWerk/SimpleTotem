#!/usr/bin/env bash
# Compila instalador e desinstalador SimpleTotem com PyInstaller.
# Execute a partir da raiz do projeto: bash installer/build.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/installer"

# Usa o pyinstaller do venv do backend
PYINSTALLER="$ROOT/SimpleTotem-backend/.venv/bin/pyinstaller"
if [ ! -x "$PYINSTALLER" ]; then
  PYINSTALLER="$(which pyinstaller 2>/dev/null || true)"
fi
if [ -z "$PYINSTALLER" ] || [ ! -x "$PYINSTALLER" ]; then
  echo "ERRO: pyinstaller não encontrado"
  exit 1
fi

BACKEND_BIN="$ROOT/SimpleTotem-backend/dist/SimpleTotem-backend"
LAUNCHER_BIN="$ROOT/launcher/dist/SimpleTotem"
UI_DIR="$ROOT/SimpleTotem/dist/SimpleTotem-ui"
SCRIPT_DIR="$ROOT/script"
ENV_EXAMPLE="$ROOT/SimpleTotem/.env.example"

echo "=== SimpleTotem Build ==="

# Verificações
for item in "$BACKEND_BIN" "$LAUNCHER_BIN" "$UI_DIR" "$SCRIPT_DIR" "$ENV_EXAMPLE"; do
  if [ ! -e "$item" ]; then
    echo "ERRO: não encontrado: $item"
    exit 1
  fi
done

echo "Todos os artefatos encontrados."

# ── Instalador ────────────────────────────────────────────────────────────────
echo ""
echo "[ 1/2 ] Compilando SimpleTotem-Installer..."

"$PYINSTALLER" \
  --onefile \
  --name "SimpleTotem-Installer" \
  --add-data "$BACKEND_BIN:." \
  --add-data "$LAUNCHER_BIN:." \
  --add-data "$UI_DIR:SimpleTotem-ui" \
  --add-data "$SCRIPT_DIR:script" \
  --add-data "$ENV_EXAMPLE:." \
  --distpath "$ROOT/dist" \
  --workpath "$ROOT/installer/build_work" \
  --specpath "$ROOT/installer" \
  main.py

# ── Desinstalador ─────────────────────────────────────────────────────────────
echo ""
echo "[ 2/2 ] Compilando SimpleTotem-Desinstalador..."

"$PYINSTALLER" \
  --onefile \
  --name "SimpleTotem-Desinstalador" \
  --distpath "$ROOT/dist" \
  --workpath "$ROOT/installer/build_work" \
  --specpath "$ROOT/installer" \
  uninstall.py

# ── Resultado ─────────────────────────────────────────────────────────────────
echo ""
echo "=== Pronto ==="
echo "Instalador:     $ROOT/dist/SimpleTotem-Installer"
du -sh "$ROOT/dist/SimpleTotem-Installer"
echo "Desinstalador:  $ROOT/dist/SimpleTotem-Desinstalador"
du -sh "$ROOT/dist/SimpleTotem-Desinstalador"
