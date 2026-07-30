#!/usr/bin/env bash
# SimpleTotem — inicializador de produção
# Uso: ./start.sh [--no-gui]
# Requer: SimpleTotem-backend e SimpleTotem.AppImage na mesma pasta.

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$DIR/SimpleTotem-backend"
APPIMAGE="$DIR/SimpleTotem.AppImage"
BACKEND_URL="http://localhost:8000/empresa/status"
NO_GUI=false

for arg in "$@"; do
  [[ "$arg" == "--no-gui" ]] && NO_GUI=true
done

# ── Backend ───────────────────────────────────────────────────────────────────
if [[ ! -x "$BACKEND" ]]; then
  echo "[start.sh] ERRO: $BACKEND não encontrado ou sem permissão de execução."
  exit 1
fi

echo "[start.sh] Iniciando backend..."
"$BACKEND" >> "$DIR/dados/backend.log" 2>&1 &
BACKEND_PID=$!
echo "[start.sh] Backend PID: $BACKEND_PID"

# Aguarda backend responder (até 20s)
echo -n "[start.sh] Aguardando backend"
for i in $(seq 1 40); do
  if curl -sf "$BACKEND_URL" > /dev/null 2>&1; then
    echo " OK"
    break
  fi
  echo -n "."
  sleep 0.5
  if [[ $i -eq 40 ]]; then
    echo " TIMEOUT — continuando mesmo assim"
  fi
done

# ── Frontend ──────────────────────────────────────────────────────────────────
if $NO_GUI; then
  echo "[start.sh] --no-gui: backend rodando em background (PID $BACKEND_PID)"
  wait "$BACKEND_PID"
else
  if [[ ! -x "$APPIMAGE" ]]; then
    echo "[start.sh] AVISO: $APPIMAGE não encontrado. Apenas o backend foi iniciado."
    wait "$BACKEND_PID"
    exit 0
  fi
  echo "[start.sh] Iniciando interface..."
  # Passa APPIMAGE para o Electron encontrar o backend adjacente
  APPIMAGE="$APPIMAGE" "$APPIMAGE" &
  GUI_PID=$!

  # Encerra backend quando a interface fechar
  wait "$GUI_PID"
  echo "[start.sh] Interface encerrada. Encerrando backend..."
  kill "$BACKEND_PID" 2>/dev/null || true
fi
