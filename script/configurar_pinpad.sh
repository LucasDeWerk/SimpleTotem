#!/usr/bin/env bash
# Configura permissões e porta do pinpad Gertec PPC930 no CliSiTef.ini
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RULES_SRC="$ROOT/script/99-pinpad-gertec.rules"
RULES_DST="/etc/udev/rules.d/99-pinpad-gertec.rules"

if [ "$(id -u)" -eq 0 ]; then
  SUDO=""
  RUN_USER="${SUDO_USER:-totem}"
else
  SUDO="sudo"
  RUN_USER="${USER:-totem}"
fi

echo "==> Instalando regra udev para pinpad Gertec..."
$SUDO cp "$RULES_SRC" "$RULES_DST"
$SUDO udevadm control --reload-rules
$SUDO udevadm trigger --subsystem-match=tty

echo "==> Adicionando usuário $RUN_USER ao grupo dialout..."
$SUDO usermod -aG dialout "$RUN_USER" || true

chmod +x "$ROOT/script/run_sitef_worker.sh" 2>/dev/null || true

echo "==> Detectando pinpad e atualizando CliSiTef.ini..."
python3 "$ROOT/script/pinpad_config.py" --configurar || \
  python3 "$ROOT/script/pinpad_config.py" --status

echo ""
echo "Dispositivos seriais:"
ls -la /dev/ttyACM* /dev/pinpad-gertec 2>/dev/null || true
