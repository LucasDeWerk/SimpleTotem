import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from core.credential_crypto import encrypt_secret
from models.orm import ApiSessao

logger = logging.getLogger(__name__)

SESSAO_CHAVE = "default"


def save_session(
    db: Session,
    *,
    token: str,
    id_saas: int,
    id_empresa: int,
    email: str,
    os_usuario: Optional[str] = None,
    senha_simples: Optional[str] = None,
    senha_os: Optional[str] = None,
    expira_em: Optional[int] = None,
) -> ApiSessao:
    row = db.query(ApiSessao).filter(ApiSessao.chave == SESSAO_CHAVE).first()
    if not row:
        row = ApiSessao(chave=SESSAO_CHAVE)
        db.add(row)
    row.token = token
    row.id_saas = id_saas
    row.id_empresa = id_empresa
    row.email = email
    row.os_usuario = os_usuario or ""
    if senha_simples:
        row.senha_simples_enc = encrypt_secret(senha_simples)
    if senha_os:
        row.senha_os_enc = encrypt_secret(senha_os)
    row.expira_em = expira_em
    row.dh_login = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    db.refresh(row)
    return row


def save_terminal_session(
    db: Session,
    *,
    jwt_token: str,
    terminal_id: int,
    terminal_token: str,
    senha_terminal: str,
    email: Optional[str] = None,
    senha_simples: Optional[str] = None,
    id_saas: Optional[int] = None,
    id_empresa: Optional[int] = None,
) -> ApiSessao:
    """Persiste credenciais completas do totem (chamado após login de 3 passos)."""
    row = db.query(ApiSessao).filter(ApiSessao.chave == SESSAO_CHAVE).first()
    if not row:
        row = ApiSessao(chave=SESSAO_CHAVE)
        db.add(row)
    row.token = jwt_token
    row.terminal_id = terminal_id
    row.terminal_token = terminal_token
    row.senha_terminal_enc = encrypt_secret(senha_terminal)
    if email:
        row.email = email
    if senha_simples:
        row.senha_simples_enc = encrypt_secret(senha_simples)
    if id_saas is not None:
        row.id_saas = id_saas
    if id_empresa is not None:
        row.id_empresa = id_empresa
    row.dh_login = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    db.refresh(row)
    return row


def update_tokens(db: Session, *, jwt_token: str, terminal_token: str) -> None:
    """Atualiza apenas os tokens após relogin automático."""
    row = db.query(ApiSessao).filter(ApiSessao.chave == SESSAO_CHAVE).first()
    if not row:
        return
    row.token = jwt_token
    row.terminal_token = terminal_token
    row.dh_login = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.commit()


def get_session(db: Session) -> Optional[ApiSessao]:
    return db.query(ApiSessao).filter(ApiSessao.chave == SESSAO_CHAVE).first()


def apply_session_to_app(request: Request, sessao: ApiSessao) -> None:
    request.app.state.external_api_token = sessao.token
    request.app.state.id_saas = sessao.id_saas
    request.app.state.id_empresa = sessao.id_empresa
    request.app.state.simplesfique_email = sessao.email
    request.app.state.os_usuario = sessao.os_usuario


def restore_session_to_app(app, db: Session) -> bool:
    sessao = get_session(db)
    if not sessao or not sessao.token:
        return False
    app.state.external_api_token = sessao.token
    app.state.id_saas = sessao.id_saas
    app.state.id_empresa = sessao.id_empresa
    app.state.simplesfique_email = sessao.email
    app.state.os_usuario = sessao.os_usuario
    logger.info(
        "Sessão SimpleSfique restaurada | saas=%s empresa=%s email=%s terminal=%s",
        sessao.id_saas,
        sessao.id_empresa,
        sessao.email,
        sessao.terminal_id,
    )
    return True


def sessao_to_dict(sessao: Optional[ApiSessao]) -> Optional[Dict[str, Any]]:
    """Retorno legado para o painel admin."""
    if not sessao or not sessao.token:
        return None
    return {
        "id_saas": sessao.id_saas,
        "id_empresa": sessao.id_empresa,
        "email": sessao.email,
        "os_usuario": sessao.os_usuario,
        "expira_em": sessao.expira_em,
        "dh_login": sessao.dh_login,
        "token_ativo": True,
    }


def sessao_to_dict_completa(sessao: Optional[ApiSessao]) -> Optional[Dict[str, Any]]:
    """Inclui tokens e dados do terminal — usado pelo frontend do totem."""
    if not sessao:
        return None
    return {
        "id_saas": sessao.id_saas,
        "id_empresa": sessao.id_empresa,
        "email": sessao.email,
        "os_usuario": sessao.os_usuario,
        "jwt_token": sessao.token or "",
        "terminal_id": sessao.terminal_id,
        "terminal_token": sessao.terminal_token or "",
        "expira_em": sessao.expira_em,
        "dh_login": sessao.dh_login,
        "configurado": bool(sessao.terminal_token and sessao.terminal_id),
    }


def pending_credentials(sessao: Optional[ApiSessao]) -> Dict[str, Optional[str]]:
    if not sessao:
        return {}
    return {
        "email_simples": sessao.email,
        "senha_simples_enc": sessao.senha_simples_enc,
        "usuario_os": sessao.os_usuario,
        "senha_os_enc": sessao.senha_os_enc,
    }
