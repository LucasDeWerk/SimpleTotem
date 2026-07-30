"""hardware.py — Cache, categorias e handlers de dispositivos USB.
Importado por device_service.py via sys.path (SCRIPT_DIR).
"""
from __future__ import annotations

import os
import glob as _glob


# ─── Cache em memória ──────────────────────────────────────────────────────────

class _Cache:
    def __init__(self):
        self._data: dict[str, dict] = {}

    def salvar(self, categoria: str, vendor_id: str, product_id: str, nome: str = "", descricao: str = "") -> None:
        self._data[categoria] = {
            "vendor_id": vendor_id.lower(),
            "product_id": product_id.lower(),
            "nome": nome,
            "descricao": descricao,
        }

    def obter(self, categoria: str) -> dict | None:
        return self._data.get(categoria)

    def remover(self, categoria: str) -> None:
        self._data.pop(categoria, None)

    def listar(self) -> dict:
        return dict(self._data)


cache = _Cache()


# ─── Categorias suportadas ────────────────────────────────────────────────────

CATEGORIAS_DEF: dict[str, dict] = {
    "impressora": {
        "label": "Impressora Térmica",
        "interface": "usb",
        "perm_tipo": "impressora",
    },
    "terminal_pagamento": {
        "label": "Pinpad / Terminal de Pagamento",
        "interface": "usb",
        "perm_tipo": "pinpad",
    },
    "leitor_barcode": {
        "label": "Leitor de Código de Barras",
        "interface": "usb",
        "perm_tipo": "leitor",
    },
}


class _Categorias:
    CATEGORIAS = CATEGORIAS_DEF

    def listar_categorias(self) -> list[dict]:
        return [
            {"categoria": k, "label": v["label"], "interface": v["interface"]}
            for k, v in self.CATEGORIAS.items()
        ]


categorias = _Categorias()


# ─── Handlers de dispositivos USB ─────────────────────────────────────────────

def _usb_path(vendor_id: str, product_id: str) -> str | None:
    for dev in _glob.glob("/sys/bus/usb/devices/*"):
        vid_file = os.path.join(dev, "idVendor")
        pid_file = os.path.join(dev, "idProduct")
        try:
            with open(vid_file) as f:
                vid = f.read().strip()
            with open(pid_file) as f:
                pid = f.read().strip()
            if vid.lower() == vendor_id.lower() and pid.lower() == product_id.lower():
                return dev
        except OSError:
            continue
    return None


def _read_sysfs(path: str, filename: str, default: str = "") -> str:
    try:
        with open(os.path.join(path, filename)) as f:
            return f.read().strip()
    except OSError:
        return default


def _acesso_ok(vendor_id: str, product_id: str) -> bool:
    sysfs = _usb_path(vendor_id, product_id)
    if not sysfs:
        return False
    busnum = _read_sysfs(sysfs, "busnum")
    devnum = _read_sysfs(sysfs, "devnum")
    if busnum and devnum:
        node = f"/dev/bus/usb/{int(busnum):03d}/{int(devnum):03d}"
        return os.access(node, os.R_OK | os.W_OK)
    return False


class _Handlers:
    def status_dispositivo(self, categoria: str, vendor_id: str, product_id: str) -> dict:
        sysfs = _usb_path(vendor_id, product_id)
        conectado = sysfs is not None
        acesso = _acesso_ok(vendor_id, product_id) if conectado else False

        detalhes: dict = {}
        if sysfs:
            detalhes["fabricante"] = _read_sysfs(sysfs, "manufacturer")
            detalhes["produto"] = _read_sysfs(sysfs, "product")
            detalhes["serial"] = _read_sysfs(sysfs, "serial")

        return {
            "conectado": conectado,
            "acesso_ok": acesso,
            "detalhes": detalhes,
        }

    def configurar_dispositivo(
        self,
        categoria: str,
        vendor_id: str,
        product_id: str,
        nome: str = "",
        fabricante: str = "",
    ) -> dict:
        sysfs = _usb_path(vendor_id, product_id)
        resultado: dict = {"nome": nome, "fabricante": fabricante}
        if sysfs:
            resultado["nome"] = nome or _read_sysfs(sysfs, "product") or "Dispositivo USB"
            resultado["fabricante"] = fabricante or _read_sysfs(sysfs, "manufacturer") or ""
        return resultado


handlers = _Handlers()
