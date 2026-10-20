"""Cliente da API Ticketera (venda + tickets de retirada).

O JWT vive na sessão persistida (ApiSessao.token). Em 401 o login é refeito
com as credenciais salvas e a chamada é repetida UMA vez — exceto na venda,
que nunca é reenviada automaticamente (a API não deduplica).
"""

import logging
import os
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

import core.config  # noqa: F401  (carrega o .env antes do getenv)
from core.credential_crypto import decrypt_secret
from services import api_session

logger = logging.getLogger(__name__)

TICKETERA_URL = os.getenv("TICKETERA_URL", "").strip().rstrip("/")
TIMEOUT = httpx.Timeout(30.0, connect=10.0)
TIMEOUT_VENDA = httpx.Timeout(90.0, connect=10.0)


def base_url() -> str:
    if not TICKETERA_URL:
        raise HTTPException(status_code=503, detail="TICKETERA_URL não configurada no .env")
    return f"{TICKETERA_URL}/api/v1"


def mensagem_erro(resp: httpx.Response) -> str:
    """erro → message → primeiro item de errors."""
    try:
        data = resp.json()
    except ValueError:
        return f"Erro {resp.status_code} da Ticketera"
    if isinstance(data, dict):
        if data.get("erro"):
            return str(data["erro"])
        if data.get("message"):
            return str(data["message"])
        errors = data.get("errors")
        if isinstance(errors, dict):
            for msgs in errors.values():
                if isinstance(msgs, list) and msgs:
                    return str(msgs[0])
                if isinstance(msgs, dict):
                    for sub in msgs.values():
                        if isinstance(sub, list) and sub:
                            return str(sub[0])
    return f"Erro {resp.status_code} da Ticketera"


def _raise(resp: httpx.Response) -> None:
    logger.warning(
        "Ticketera %s %s -> %s: %s",
        resp.request.method, resp.request.url.path, resp.status_code, resp.text[:600],
    )
    detail: Any = mensagem_erro(resp)
    try:
        body = resp.json()
        if isinstance(body, dict) and resp.status_code in (422, 502) and body.get("tipo"):
            detail = {"mensagem": detail, **{k: body[k] for k in ("tipo", "cStat", "xMotivo") if k in body}}
    except ValueError:
        pass
    raise HTTPException(status_code=resp.status_code, detail=detail)


async def login(email: str, senha: str) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(
                f"{base_url()}/auth/login",
                json={"email": email, "senha": senha},
                headers={"Accept": "application/json"},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Sem conexão com a Ticketera: {exc}") from exc
    if resp.status_code != 200:
        _raise(resp)
    return resp.json()


async def relogin(db: Session, request: Request) -> str:
    sessao = api_session.get_session(db)
    if not sessao or not sessao.email or not sessao.senha_simples_enc:
        raise HTTPException(status_code=401, detail="Sessão expirada — refaça o login do totem")
    senha = decrypt_secret(sessao.senha_simples_enc)
    data = await login(sessao.email, senha)
    token = data["token"]
    api_session.update_tokens(db, jwt_token=token, terminal_token=token)
    request.app.state.external_api_token = token
    logger.info("Ticketera: token renovado")
    return token


async def call(
    db: Session,
    request: Request,
    method: str,
    path: str,
    *,
    json: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    terminal_id: Optional[int] = None,
    retry_401: bool = True,
    timeout: httpx.Timeout = TIMEOUT,
) -> Any:
    sessao = api_session.get_session(db)
    token = sessao.token if sessao else None
    if not token:
        raise HTTPException(status_code=401, detail="Totem sem sessão — faça o login")
    tid = terminal_id or (sessao.terminal_id if sessao else None)

    for tentativa in (1, 2):
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        if tid:
            headers["X-Terminal-Id"] = str(tid)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.request(
                    method, f"{base_url()}/{path.lstrip('/')}", json=json, params=params, headers=headers
                )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail=f"Sem conexão com a Ticketera: {exc}") from exc

        if resp.status_code == 401 and retry_401 and tentativa == 1:
            token = await relogin(db, request)
            continue
        if resp.status_code >= 400:
            _raise(resp)
        return resp.json()
