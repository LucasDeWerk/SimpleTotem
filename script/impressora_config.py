#!/usr/bin/env python3
"""Impressora genérica — qualquer VID:PID USB configurado no totem."""

from __future__ import annotations

import argparse
import json
import sys

from hardware.cache import obter as cache_obter
from hardware.handlers import configurar_dispositivo, status_dispositivo


def _vid_pid() -> tuple[str, str]:
    cfg = cache_obter("impressora")
    if cfg:
        return cfg["vendor_id"], cfg["product_id"]
    return "", ""


def status() -> dict:
    vid, pid = _vid_pid()
    if not vid:
        return {
            "detectado": False,
            "configurado": False,
            "mensagem": "Nenhuma impressora atribuída. Configure em Admin → Dispositivos.",
        }
    info = status_dispositivo("impressora", vid, pid)
    return {
        **info,
        "detectado": info["conectado"],
        "produto": info["detalhes"].get("produto"),
        "caminho_usb": info["detalhes"].get("caminho_usb"),
        "configurado": True,
    }


def configurar() -> dict:
    vid, pid = _vid_pid()
    if not vid:
        raise RuntimeError("Atribua uma impressora em Admin → Dispositivos primeiro.")
    return configurar_dispositivo("impressora", vid, pid)


def main() -> int:
    parser = argparse.ArgumentParser(description="Impressora genérica (qualquer marca)")
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
