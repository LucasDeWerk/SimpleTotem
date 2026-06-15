#!/usr/bin/env bash
# Permissões USB da impressora térmica Epson (escpos-usb / libusb)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RULES_SRC="$ROOT/script/99-impressora-epson.rules"
RULES_DST="/etc/udev/rules.d/99-impressora-epson.rules"

if [ "$(id -u)" -eq 0 ]; then
  SUDO=""
  RUN_USER="${SUDO_USER:-totem}"
else
  SUDO="sudo"
  RUN_USER="${USER:-totem}"
fi

echo "==> Instalando regra udev para impressora Epson..."
$SUDO cp "$RULES_SRC" "$RULES_DST"
$SUDO udevadm control --reload-rules
$SUDO udevadm trigger --subsystem-match=usb

echo "==> Adicionando usuário $RUN_USER ao grupo lp (fallback CUPS/usblp)..."
$SUDO usermod -aG lp "$RUN_USER" 2>/dev/null || true

echo ""
echo "Dispositivos USB Epson:"
lsusb -d 04b8:0e27 2>/dev/null || echo "  (impressora não conectada no momento)"
ls -la /dev/bus/usb/*/* 2>/dev/null | grep -E "04b8|lp" || true
ls -la /dev/usb/lp* 2>/dev/null || true

echo ""
echo "Regra instalada: $RULES_DST"
echo "Reinicie o Electron (ou faça logout/login) após a instalação."
