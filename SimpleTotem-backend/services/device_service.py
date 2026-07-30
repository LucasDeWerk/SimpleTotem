"""Hardware genérico — qualquer VID:PID em qualquer categoria."""

from __future__ import annotations

import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from core.config import SCRIPT_DIR as _SCRIPT_DIR
from core.database import SessionLocal
from models.orm import Hardware

logger = logging.getLogger(__name__)
_CATEGORIAS_IDS = ("impressora", "terminal_pagamento", "leitor_barcode")


def _ensure_script_path() -> None:
    path = str(_SCRIPT_DIR)
    if path not in sys.path:
        sys.path.insert(0, path)


def _hw():
    _ensure_script_path()
    from hardware import cache, categorias, handlers  # noqa: WPS433
    return cache, categorias, handlers


def sudo_sem_senha_disponivel() -> bool:
    try:
        return subprocess.run(["sudo", "-n", "true"], capture_output=True, timeout=5).returncode == 0
    except Exception:
        return False


def _aplicar_permissao(vendor_id: str, product_id: str, tipo: str) -> None:
    if not sudo_sem_senha_disponivel():
        return
    script = _SCRIPT_DIR / "aplicar_permissao_dispositivo.sh"
    if not script.exists():
        return
    try:
        proc = subprocess.run(
            ["sudo", "-n", "bash", str(script), vendor_id, product_id, tipo],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.stdout:
            logger.info("[Hardware] %s", proc.stdout.strip())
        if proc.returncode != 0 and proc.stderr:
            logger.warning("[Hardware] %s", proc.stderr.strip())
    except Exception as exc:
        logger.warning("[Hardware] Permissão: %s", exc)


def _obter_config_db(db: Session, categoria: str) -> Hardware | None:
    return (
        db.query(Hardware)
        .filter(Hardware.tipo_dispositivo == categoria, Hardware.ativo == 1)
        .order_by(Hardware.id.desc())
        .first()
    )


def _salvar_config_db(
    db: Session,
    categoria: str,
    vendor_id: str,
    product_id: str,
    nome: str,
    fabricante: str,
    interface: str,
) -> Hardware:
    now = datetime.now(timezone.utc).isoformat()
    descricao = f"{fabricante} {nome}".strip()

    hw = _obter_config_db(db, categoria)
    if hw:
        hw.nome = nome
        hw.vendor_id = vendor_id.lower()
        hw.product_id = product_id.lower()
        hw.descricao = descricao
        hw.driver_id = interface
        hw.ativo = 1
        hw.dhalt = now
    else:
        hw = Hardware(
            tipo_dispositivo=categoria,
            nome=nome,
            vendor_id=vendor_id.lower(),
            product_id=product_id.lower(),
            descricao=descricao,
            driver_id=interface,
            ativo=1,
            dhinc=now,
        )
        db.add(hw)

    db.commit()
    db.refresh(hw)
    return hw


def listar_categorias() -> list[dict]:
    _, categorias, _ = _hw()
    return categorias.listar_categorias()


def status_categoria(categoria: str, db: Session | None = None) -> dict:
    _, categorias, handlers = _hw()
    meta = categorias.CATEGORIAS.get(categoria)
    if not meta:
        raise ValueError(f"Categoria inválida: {categoria}")

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        hw = _obter_config_db(db, categoria)
        if not hw:
            return {
                "categoria": categoria,
                "label": meta["label"],
                "interface": meta["interface"],
                "configurado": None,
                "conectado": False,
                "acesso_ok": False,
                "ok": False,
            }

        live = handlers.status_dispositivo(categoria, hw.vendor_id, hw.product_id)
        return {
            "categoria": categoria,
            "label": meta["label"],
            "interface": meta["interface"],
            "configurado": {
                "id": hw.id,
                "nome": hw.nome,
                "fabricante": hw.descricao,
                "vendor_id": hw.vendor_id,
                "product_id": hw.product_id,
                "interface": hw.driver_id or meta["interface"],
            },
            "conectado": live["conectado"],
            "acesso_ok": live["acesso_ok"],
            "detalhes": live.get("detalhes", {}),
            "ok": live["conectado"] and live["acesso_ok"],
            "dica_permissao": (
                f"sudo bash script/aplicar_permissao_dispositivo.sh "
                f"{hw.vendor_id} {hw.product_id} {meta['perm_tipo']}"
                if live["conectado"] and not live["acesso_ok"]
                else None
            ),
        }
    finally:
        if close_db:
            db.close()


def status_geral() -> dict:
    db = SessionLocal()
    try:
        categorias_status = {
            cat: status_categoria(cat, db) for cat in _CATEGORIAS_IDS
        }
    finally:
        db.close()

    return {
        "categorias": categorias_status,
        "tipos": listar_categorias(),
        "sudo_sem_senha": sudo_sem_senha_disponivel(),
    }


def atribuir_dispositivo(
    categoria: str,
    vendor_id: str,
    product_id: str,
    nome: str = "",
    fabricante: str = "",
) -> dict:
    """
    Atribui QUALQUER dispositivo USB a uma categoria e aplica configuração.
    Mesmo fluxo para Bematech, Epson, Gertec, Ingenico, etc.
    """
    _, categorias, handlers = _hw()
    cache, _, _ = _hw()
    meta = categorias.CATEGORIAS.get(categoria)
    if not meta:
        raise ValueError(f"Categoria inválida: {categoria}")

    vid = vendor_id.lower().strip()
    pid = product_id.lower().strip()
    if not vid or not pid:
        raise ValueError("vendor_id e product_id são obrigatórios")

    live = handlers.status_dispositivo(categoria, vid, pid)
    if live["conectado"] and not live["acesso_ok"]:
        _aplicar_permissao(vid, pid, meta["perm_tipo"])
        live = handlers.status_dispositivo(categoria, vid, pid)

    info = handlers.configurar_dispositivo(
        categoria, vid, pid,
        nome=nome or live["detalhes"].get("produto", ""),
        fabricante=fabricante or live["detalhes"].get("fabricante", ""),
    )

    db = SessionLocal()
    try:
        hw = _salvar_config_db(
            db, categoria, vid, pid,
            nome=info.get("nome", nome) or "Dispositivo USB",
            fabricante=info.get("fabricante", fabricante),
            interface=meta["interface"],
        )
    finally:
        db.close()

    cache.salvar(categoria, vid, pid, info.get("nome", nome), info.get("fabricante", fabricante))

    result = status_categoria(categoria)
    result["hardware_id"] = hw.id
    result["sudo_sem_senha"] = sudo_sem_senha_disponivel()
    return result


def remover_dispositivo(categoria: str) -> None:
    cache, _, _ = _hw()
    db = SessionLocal()
    try:
        hw = _obter_config_db(db, categoria)
        if hw:
            db.delete(hw)
            db.commit()
    finally:
        db.close()
    cache.remover(categoria)


def _sincronizar_cache_do_banco() -> None:
    cache, _, _ = _hw()
    db = SessionLocal()
    try:
        for cat in _CATEGORIAS_IDS:
            hw = _obter_config_db(db, cat)
            if hw:
                cache.salvar(cat, hw.vendor_id, hw.product_id, hw.nome or "", hw.descricao or "")
    finally:
        db.close()


def bootstrap_hardware() -> dict:
    """Na inicialização: valida dispositivos já configurados no banco."""
    _sincronizar_cache_do_banco()
    info = status_geral()
    for cat, st in info.get("categorias", {}).items():
        cfg = st.get("configurado")
        if not cfg:
            logger.info("[Hardware][%s] Não configurado", cat)
            continue
        if st.get("ok"):
            logger.info(
                "[Hardware][%s] OK — %s (%s:%s)",
                cat, cfg["nome"], cfg["vendor_id"], cfg["product_id"],
            )
        elif st.get("conectado"):
            logger.warning(
                "[Hardware][%s] Sem permissão — %s:%s. %s",
                cat, cfg["vendor_id"], cfg["product_id"], st.get("dica_permissao", ""),
            )
        else:
            logger.warning(
                "[Hardware][%s] Desconectado — %s (%s:%s)",
                cat, cfg["nome"], cfg["vendor_id"], cfg["product_id"],
            )
    return info


# ── Compat legado (endpoints antigos) ─────────────────────────────────────────

def listar_catalogo() -> list[dict]:
    return listar_categorias()


def configurar_categoria(categoria: str) -> dict:
    raise RuntimeError(
        "Selecione um dispositivo USB na tela de hardware e atribua à categoria. "
        "Qualquer marca é suportada via VID:PID."
    )


def configurar_driver(_driver_id: str) -> dict:
    raise RuntimeError("Use POST /hardware/atribuir com vendor_id e product_id do dispositivo.")
