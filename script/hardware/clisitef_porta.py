"""Atualização genérica da porta serial no CliSiTef.ini (qualquer pinpad)."""

from __future__ import annotations

import re
from pathlib import Path

INI_PATH = Path(__file__).resolve().parent.parent / "CliSiTef.ini"


def ler_porta() -> str:
    if not INI_PATH.exists():
        return ""
    conteudo = INI_PATH.read_text(encoding="latin-1")
    match = re.search(r"^\s*Porta\s*=\s*(.+)\s*$", conteudo, re.MULTILINE)
    return match.group(1).strip() if match else ""


def atualizar_porta(porta: str) -> None:
    if not porta:
        return
    conteudo = INI_PATH.read_text(encoding="latin-1") if INI_PATH.exists() else ""

    if re.search(r"^\s*Porta\s*=", conteudo, re.MULTILINE):
        conteudo = re.sub(
            r"^\s*Porta\s*=.*$",
            f"Porta={porta}",
            conteudo,
            count=1,
            flags=re.MULTILINE,
        )
    elif "[PinPadCompartilhado]" in conteudo:
        conteudo = conteudo.replace(
            "[PinPadCompartilhado]\n",
            f"[PinPadCompartilhado]\nPorta={porta}\n",
        )
    else:
        conteudo += f"\n[PinPadCompartilhado]\nPorta={porta}\n"

    INI_PATH.write_text(conteudo, encoding="latin-1")
