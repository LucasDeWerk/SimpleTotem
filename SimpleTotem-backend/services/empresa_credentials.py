"""Persistência e leitura de credenciais da empresa (criptografadas)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from core.credential_crypto import decrypt_secret, encrypt_secret
from models.orm import Empresa


def apply_credentials(
    empresa_data: Dict[str, Any],
    *,
    email_simples: Optional[str] = None,
    senha_simples: Optional[str] = None,
    usuario_os: Optional[str] = None,
    senha_os: Optional[str] = None,
) -> Dict[str, Any]:
    if email_simples:
        empresa_data["email_simples"] = email_simples.strip()
    if senha_simples:
        empresa_data["senha_simples"] = encrypt_secret(senha_simples)
    if usuario_os:
        empresa_data["usuario_os"] = usuario_os.strip()
    if senha_os:
        empresa_data["senha_os"] = encrypt_secret(senha_os)
    return empresa_data


def update_os_credentials(db: Session, usuario: str, senha: str) -> None:
    empresa = db.query(Empresa).first()
    if not empresa:
        return
    empresa.usuario_os = usuario.strip()
    empresa.senha_os = encrypt_secret(senha)
    db.commit()


def get_credentials(db: Session, id_saas: int, id_empresa: int) -> Optional[Dict[str, str]]:
    empresa = (
        db.query(Empresa)
        .filter(Empresa.id_saas == id_saas, Empresa.id_empresa == id_empresa)
        .first()
    )
    if not empresa:
        return None
    return {
        "email_simples": empresa.email_simples or "",
        "senha_simples": decrypt_secret(empresa.senha_simples) if empresa.senha_simples else "",
        "usuario_os": empresa.usuario_os or "",
        "senha_os": decrypt_secret(empresa.senha_os) if empresa.senha_os else "",
    }
