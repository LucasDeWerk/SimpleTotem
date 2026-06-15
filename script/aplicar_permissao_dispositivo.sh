#!/usr/bin/env bash
# Permissão udev genérica para QUALQUER dispositivo USB (impressora ou pinpad serial)
# Uso: sudo bash script/aplicar_permissao_dispositivo.sh <VID> <PID> [usb|serial]
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Execute com sudo."
  exit 1
fi

VID="${1:?VID obrigatório (ex: 04b8)}"
PID="${2:?PID obrigatório (ex: 0e27)}"
TIPO="${3:-usb}"
VID=$(echo "$VID" | tr '[:upper:]' '[:lower:]')
PID=$(echo "$PID" | tr '[:upper:]' '[:lower:]')

RULES_DST="/etc/udev/rules.d/99-totem-${VID}-${PID}.rules"

if [ "$TIPO" = "serial" ]; then
  cat > "$RULES_DST" <<EOF
# Totem — pinpad/serial ${VID}:${PID}
SUBSYSTEM=="tty", ATTRS{idVendor}=="${VID}", ATTRS{idProduct}=="${PID}", \\
  MODE="0666", GROUP="dialout"
EOF
  echo "Regra serial instalada: $RULES_DST"
  udevadm control --reload-rules
  udevadm trigger --subsystem-match=tty
else
  cat > "$RULES_DST" <<EOF
# Totem — USB ${VID}:${PID}
SUBSYSTEM=="usb", ATTR{idVendor}=="${VID}", ATTR{idProduct}=="${PID}", \\
  MODE="0666", GROUP="plugdev"
EOF
  echo "Regra USB instalada: $RULES_DST"
  udevadm control --reload-rules
  udevadm trigger --subsystem-match=usb
fi

RUN_USER="${SUDO_USER:-totem}"
usermod -aG plugdev "$RUN_USER" 2>/dev/null || true
usermod -aG dialout "$RUN_USER" 2>/dev/null || true

echo "Permissão aplicada para ${VID}:${PID} (${TIPO})."
echo "Reconecte o cabo USB ou reinicie o app."
