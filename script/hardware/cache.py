"""Cache local de dispositivos configurados (lido pelo sitef_worker sem DB)."""

from __future__ import annotations

import json
from pathlib import Path

CACHE_PATH = Path(__file__).resolve().parent.parent / ".hardware_cache.json"


def ler() -> dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def salvar(categoria: str, vendor_id: str, product_id: str, nome: str = "", fabricante: str = "") -> None:
    data = ler()
    data[categoria] = {
        "vendor_id": vendor_id.lower(),
        "product_id": product_id.lower(),
        "nome": nome,
        "fabricante": fabricante,
    }
    CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def remover(categoria: str) -> None:
    data = ler()
    data.pop(categoria, None)
    CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def obter(categoria: str) -> dict | None:
    return ler().get(categoria)
