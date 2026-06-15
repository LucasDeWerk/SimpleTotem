"""
Handlers genéricos por categoria — qualquer VID:PID, qualquer marca.
"""

from __future__ import annotations

from .categorias import CATEGORIAS
from .clisitef_porta import atualizar_porta, ler_porta
from .usb import (
    encontrar_por_vid_pid,
    encontrar_porta_serial,
    verificar_acesso_caminho,
)


def _meta_categoria(categoria: str) -> dict:
    if categoria not in CATEGORIAS:
        raise ValueError(f"Categoria inválida: {categoria}")
    return CATEGORIAS[categoria]


def status_dispositivo(categoria: str, vendor_id: str, product_id: str) -> dict:
    """Verifica se o dispositivo configurado está conectado e acessível."""
    meta = _meta_categoria(categoria)
    vid = vendor_id.lower()
    pid = product_id.lower()

    base = {
        "categoria": categoria,
        "vendor_id": vid,
        "product_id": pid,
        "interface": meta["interface"],
        "conectado": False,
        "acesso_ok": False,
        "detalhes": {},
    }

    if meta["interface"] == "serial":
        porta = encontrar_porta_serial(vid, pid)
        porta_ini = ler_porta()
        porta_uso = porta_ini or porta or ""
        base["detalhes"] = {
            "porta_detectada": porta,
            "porta_configurada": porta_ini or porta,
        }
        base["conectado"] = porta is not None
        base["acesso_ok"] = verificar_acesso_caminho(porta_uso) if porta_uso else False
        return base

    # USB (impressora, leitor)
    dev = encontrar_por_vid_pid(vid, pid)
    if dev:
        caminho = dev.get("caminho_usb", "")
        base["conectado"] = True
        base["detalhes"] = {
            **dev,
            "caminho_usb": caminho,
        }
        base["acesso_ok"] = verificar_acesso_caminho(caminho) if caminho else True
    return base


def configurar_dispositivo(
    categoria: str,
    vendor_id: str,
    product_id: str,
    nome: str = "",
    fabricante: str = "",
) -> dict:
    """
    Aplica configuração genérica para o VID:PID na categoria.
    Não depende de marca — só do tipo de interface.
    """
    meta = _meta_categoria(categoria)
    vid = vendor_id.lower()
    pid = product_id.lower()
    info = status_dispositivo(categoria, vid, pid)

    if not info["conectado"]:
        raise RuntimeError(
            f"Dispositivo {vid}:{pid} não encontrado na USB. "
            f"Conecte o cabo e tente novamente."
        )

    if meta["interface"] == "serial":
        porta = info["detalhes"].get("porta_detectada")
        if not porta:
            raise RuntimeError(
                f"Dispositivo {vid}:{pid} não expõe porta serial (ttyACM/ttyUSB)."
            )
        atualizar_porta(porta)
        info = status_dispositivo(categoria, vid, pid)
        if not info["acesso_ok"]:
            raise RuntimeError(
                f"Sem permissão em {porta}. Execute:\n"
                f"sudo bash script/aplicar_permissao_dispositivo.sh {vid} {pid} serial"
            )
    elif not info["acesso_ok"]:
        caminho = info["detalhes"].get("caminho_usb", "?")
        raise RuntimeError(
            f"Sem permissão USB em {caminho}. Execute:\n"
            f"sudo bash script/aplicar_permissao_dispositivo.sh {vid} {pid} usb"
        )

    info["nome"] = nome or info["detalhes"].get("produto") or "Dispositivo USB"
    info["fabricante"] = fabricante or info["detalhes"].get("fabricante") or ""
    info["ok"] = info["conectado"] and info["acesso_ok"]
    return info


def garantir_pinpad_configurado(vendor_id: str, product_id: str) -> str:
    """Usado pelo sitef_worker — atualiza CliSiTef.ini para o pinpad configurado."""
    porta = encontrar_porta_serial(vendor_id, product_id)
    if porta:
        atualizar_porta(porta)
    return ler_porta() or porta or ""
