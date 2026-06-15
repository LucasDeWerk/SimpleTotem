"""Categorias de periférico — independentes de marca/modelo."""

from __future__ import annotations

CATEGORIAS: dict[str, dict] = {
    "impressora": {
        "label": "Impressora Térmica",
        "interface": "usb",
        "descricao": "Qualquer impressora ESC/POS via USB (Bematech, Epson, Elgin, etc.)",
        "perm_tipo": "usb",
        "tem_teste": True,
    },
    "terminal_pagamento": {
        "label": "Terminal de Pagamento",
        "interface": "serial",
        "descricao": "Qualquer pinpad USB serial (Gertec, Ingenico, PAX, etc.) — porta no CliSiTef.ini",
        "perm_tipo": "serial",
        "tem_teste": False,
    },
    "leitor_barcode": {
        "label": "Leitor de Código de Barras",
        "interface": "usb",
        "descricao": "Scanner USB HID — apenas identificação VID/PID",
        "perm_tipo": "usb",
        "tem_teste": False,
    },
}


def listar_categorias() -> list[dict]:
    return [
        {"id": cid, **meta}
        for cid, meta in CATEGORIAS.items()
    ]
