#!/usr/bin/env bash
# Instalação única no totem: udev + sudo sem senha + pinpad
# Executar: sudo bash script/instalar_permissoes_totem.sh
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Execute com sudo: sudo bash script/instalar_permissoes_totem.sh"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOTEM_USER="${SUDO_USER:-totem}"

echo "==> SimpleTotem — instalando permissões para usuário: $TOTEM_USER"

bash "$ROOT/script/configurar_pinpad.sh"
bash "$ROOT/script/configurar_impressora.sh"

SUDOERS_DST="/etc/sudoers.d/simpletotem"
sed \
  -e "s|@PROJECT_ROOT@|$ROOT|g" \
  -e "s|@TOTEM_USER@|$TOTEM_USER|g" \
  "$ROOT/script/simpletotem.sudoers" > "$SUDOERS_DST"
chmod 440 "$SUDOERS_DST"
visudo -c -f "$SUDOERS_DST"

chmod +x "$ROOT/script/run_sitef_worker.sh"
chmod +x "$ROOT/script/configurar_pinpad.sh"
chmod +x "$ROOT/script/configurar_impressora.sh"

echo ""
echo "Instalação concluída."
echo "  - udev: /dev/pinpad-gertec"
echo "  - udev: impressora Epson 04b8:0e27 (libusb)"
echo "  - sudo sem senha: run_sitef_worker.sh e configurar_pinpad.sh"
echo ""
echo "Reinicie o backend. Não é necessário rodar sudo manualmente no dia a dia."
