"""Utilitários USB compartilhados (sysfs / dev paths)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator


def ler_sysfs(device_path: Path, nome: str) -> str:
    path = device_path / nome
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").strip()


def iter_dispositivos_usb() -> Iterator[dict]:
    """Percorre /sys/bus/usb/devices e produz dicts com vid/pid e metadados."""
    usb_base = Path("/sys/bus/usb/devices")
    if not usb_base.exists():
        return

    for entry in usb_base.iterdir():
        vid_path = entry / "idVendor"
        pid_path = entry / "idProduct"
        if not vid_path.exists() or not pid_path.exists():
            continue

        vid = vid_path.read_text().strip().lower()
        pid = pid_path.read_text().strip().lower()
        busnum = ler_sysfs(entry, "busnum")
        devnum = ler_sysfs(entry, "devnum")
        caminho_usb = ""
        if busnum and devnum:
            caminho_usb = f"/dev/bus/usb/{int(busnum):03d}/{int(devnum):03d}"

        yield {
            "vendor_id": vid,
            "product_id": pid,
            "fabricante": ler_sysfs(entry, "manufacturer"),
            "produto": ler_sysfs(entry, "product"),
            "caminho_usb": caminho_usb,
            "sysfs": str(entry),
        }


def encontrar_por_vid_pid(vendor_id: str, product_id: str) -> dict | None:
    vid = vendor_id.lower()
    pid = product_id.lower()
    for dev in iter_dispositivos_usb():
        if dev["vendor_id"] == vid and dev["product_id"] == pid:
            return dev
    return None


def encontrar_porta_serial(vendor_id: str, product_id: str, prefixo: str = "ttyACM") -> str | None:
    """Retorna /dev/ttyACM* (ou ttyUSB*) associado ao dispositivo USB."""
    usb_base = Path("/sys/bus/usb/devices")
    if not usb_base.exists():
        return None

    vid = vendor_id.lower()
    pid = product_id.lower()

    for entry in usb_base.iterdir():
        vid_path = entry / "idVendor"
        pid_path = entry / "idProduct"
        if not vid_path.exists() or not pid_path.exists():
            continue
        if vid_path.read_text().strip().lower() != vid:
            continue
        if pid_path.read_text().strip().lower() != pid:
            continue

        for tty_dir in entry.rglob("tty"):
            for child in sorted(tty_dir.iterdir()):
                if child.name.startswith(prefixo):
                    return f"/dev/{child.name}"

    return None


def verificar_acesso_caminho(caminho: str) -> bool:
    if not caminho:
        return False
    path = Path(caminho)
    return path.exists() and os.access(path, os.R_OK | os.W_OK)


def udev_instalado(nome_arquivo: str) -> bool:
    return Path(f"/etc/udev/rules.d/{nome_arquivo}").exists()
