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
        "Sessão SimpleSfique restaurada | saas=%s empresa=%s email=%s os=%s",
        sessao.id_saas,
        sessao.id_empresa,
        sessao.email,
        sessao.os_usuario,
    )
    return True


def pending_credentials(sessao: Optional[ApiSessao]) -> Dict[str, Optional[str]]:
    if not sessao:
        return {}
    return {
        "email_simples": sessao.email,
        "senha_simples_enc": sessao.senha_simples_enc,
        "usuario_os": sessao.os_usuario,
        "senha_os_enc": sessao.senha_os_enc,
    }


def sessao_to_dict(sessao: Optional[ApiSessao]) -> Optional[Dict[str, Any]]:
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
