from typing import Any, Dict, Optional

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from services import api_session, ticketera, venda_idempotency

router = APIRouter(prefix="/ticketera", tags=["ticketera"])


@router.get("/terminais")
async def listar_terminais(request: Request, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    return await ticketera.call(db, request, "GET", "operacional/terminais")


@router.post("/terminais/{terminal_id}/validar-senha")
async def validar_senha(
    terminal_id: int,
    body: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    data = await ticketera.call(
        db, request, "POST", f"operacional/terminais/{terminal_id}/validar-senha",
        json={"senha": body.get("senha", ""), "app": "totem"},
    )
    sessao = api_session.get_session(db)
    # Ticketera usa o mesmo JWT + X-Terminal-Id; access_token mantém o contrato do front.
    data["access_token"] = sessao.token if sessao else ""
    return data


@router.get("/terminal-atual")
async def terminal_atual(request: Request, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    """Revalida o terminal salvo (senha criptografada na sessão) e devolve suas flags."""
    from core.credential_crypto import decrypt_secret

    sessao = api_session.get_session(db)
    if not sessao or not sessao.terminal_id or not sessao.senha_terminal_enc:
        raise HTTPException(status_code=404, detail="Terminal não configurado")
    return await validar_senha(
        sessao.terminal_id, {"senha": decrypt_secret(sessao.senha_terminal_enc)}, request, db, _
    )


@router.get("/terminais/{terminal_id}/produtos")
async def produtos(terminal_id: int, request: Request, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    return await ticketera.call(db, request, "GET", f"terminal/terminais/{terminal_id}/produtos", terminal_id=terminal_id)


@router.post("/venda")
async def venda(
    body: Dict[str, Any],
    request: Request,
    nfce: bool = Query(False),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """Fecha a venda sem duplicar: a API não deduplica `idempotency_key`.

    - chave já gravada → devolve a resposta original;
    - chave com tentativa incerta (5xx/timeout) → confere na Ticketera se a venda
      chegou a ser gravada antes de reenviar.
    """
    chave = str(body.get("idempotency_key") or "")
    total = venda_idempotency.total_venda(body)

    registro = venda_idempotency.obter(chave) if chave else None
    if registro and registro.get("estado") == "ok":
        return registro["resposta"]
    if registro and registro.get("estado") == "incerto":
        achada = await _buscar_venda_gravada(db, request, registro, total)
        if achada:
            resposta = {
                "pedido": achada,
                "tickets": [],
                "cupom_fiscal": None,
                "aviso_fiscal": None,
                "recuperada": True,
            }
            venda_idempotency.gravar(chave, {**registro, "estado": "ok", "resposta": resposta})
            return resposta

    inicio = venda_idempotency.agora_utc()
    try:
        resposta = await ticketera.call(
            db, request, "POST", "terminal/venda-nfce" if nfce else "terminal/venda",
            json=body, timeout=ticketera.TIMEOUT_VENDA,
        )
    except HTTPException as exc:
        if chave and exc.status_code >= 500:
            venda_idempotency.gravar(chave, {"estado": "incerto", "inicio": inicio, "terminal_id": _terminal_id(db)})
        raise
    if chave:
        venda_idempotency.gravar(chave, {"estado": "ok", "inicio": inicio, "resposta": resposta})
    return resposta


def _terminal_id(db: Session) -> Optional[int]:
    sessao = api_session.get_session(db)
    return sessao.terminal_id if sessao else None


async def _buscar_venda_gravada(db: Session, request: Request, registro: Dict[str, Any], total: float) -> Optional[Dict[str, Any]]:
    """Procura, nas vendas de hoje do terminal, uma paga com o mesmo total emitida depois da tentativa."""
    inicio = datetime.fromisoformat(registro["inicio"])
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    params = {"data": hoje, "terminal_id": registro.get("terminal_id") or _terminal_id(db)}
    try:
        dados = await ticketera.call(db, request, "GET", "terminal/vendas", params=params)
    except HTTPException:
        # Sem como conferir: não reenviar às cegas.
        raise HTTPException(status_code=503, detail="Não foi possível conferir se a venda anterior foi gravada. Tente novamente.")
    for v in dados.get("vendas", []):
        try:
            emissao = datetime.fromisoformat(str(v.get("dtemissao")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if v.get("status") == "pago" and abs(float(v.get("total") or 0) - total) < 0.01 and emissao >= inicio:
            return {"id": v.get("id"), "codigo_senha": v.get("codigo_senha"), "status": v.get("status"), "total": v.get("total")}
    return None


@router.post("/tickets/{ticket_id}/validar")
async def validar_ticket(ticket_id: str, request: Request, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    return await ticketera.call(db, request, "POST", f"terminal/tickets/{ticket_id}/validar")


@router.get("/vendas")
async def listar_vendas(
    request: Request,
    codigo_senha: Optional[str] = None,
    data: Optional[str] = None,
    terminal_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    params = {k: v for k, v in {"codigo_senha": codigo_senha, "data": data, "terminal_id": terminal_id}.items() if v}
    return await ticketera.call(db, request, "GET", "terminal/vendas", params=params)


@router.patch("/vendas/{venda_id}/cancelar")
async def cancelar_venda(
    venda_id: int, body: Dict[str, Any], request: Request,
    db: Session = Depends(get_db), _: str = Depends(get_current_user),
):
    return await ticketera.call(db, request, "PATCH", f"terminal/vendas/{venda_id}/cancelar", json={"motivo": body.get("motivo", "")})
