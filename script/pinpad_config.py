#!/usr/bin/env python3
"""Pinpad genérico — qualquer VID:PID serial configurado no totem."""

from __future__ import annotations

import argparse
import json
import sys

from hardware.cache import obter as cache_obter
from hardware.handlers import garantir_pinpad_configurado, status_dispositivo


def _vid_pid() -> tuple[str, str]:
    cfg = cache_obter("terminal_pagamento")
    if cfg:
        return cfg["vendor_id"], cfg["product_id"]
    return "", ""


def status() -> dict:
    vid, pid = _vid_pid()
    if not vid:
        return {
            "detectado": False,
            "configurado": False,
            "mensagem": "Nenhum pinpad atribuído. Configure em Admin → Dispositivos.",
        }
    info = status_dispositivo("terminal_pagamento", vid, pid)
    return {
        **info,
        "detectado": info["conectado"],
        "porta_detectada": info["detalhes"].get("porta_detectada"),
        "porta_configurada": info["detalhes"].get("porta_configurada"),
        "configurado": True,
    }


def configurar() -> dict:
    vid, pid = _vid_pid()
    if not vid:
        raise RuntimeError("Atribua um pinpad em Admin → Dispositivos primeiro.")
    from hardware.handlers import configurar_dispositivo
    return configurar_dispositivo("terminal_pagamento", vid, pid)


def garantir_configurado() -> str:
    vid, pid = _vid_pid()
    if vid and pid:
        return garantir_pinpad_configurado(vid, pid)
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Pinpad genérico (qualquer marca)")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--configurar", action="store_true")
    args = parser.parse_args()
    try:
        info = configurar() if args.configurar else status()
        print(json.dumps(info, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
