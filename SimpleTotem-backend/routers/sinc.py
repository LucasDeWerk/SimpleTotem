from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from core.database import get_db
from models.orm import Empresa
from models.schemas import (
    EmpresaOut,
    SessaoSimpleSfiqueOut,
    SessaoCompletaOut,
    SessaoTotemRequest,
    ReloginOut,
    SimpleSfiqueLoginRequest,
    SimpleSfiqueLoginResponse,
)
from services import api_session, mock_data, sync_service

router = APIRouter(prefix="/sinc", tags=["sincronizacao"])


async def call_external_api(request: Request, endpoint: str, dhsinc: Optional[str] = None):
    """Retorna dados mockados no lugar da antiga API externa SimpleSfique."""
    token = request.app.state.external_api_token

    if not token:
        raise HTTPException(status_code=503, detail="Token não disponível")

    return mock_data.mock_empresas_delta_payload()


# ── Sincronização de Empresa ───────────────────────────────────────────────────

@router.post("/empresa")
def sinc_empresa(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """Persiste dados de empresa no banco de dados"""
    try:
        if isinstance(data, list):
            empresas = data
        else:
            empresas = [data]
        
        results = {"created": 0, "updated": 0, "errors": []}
        
        for empresa_data in empresas:
            try:
                existing = db.query(Empresa).filter(
                    Empresa.id_saas == empresa_data.get("id_saas"),
                    Empresa.id_empresa == empresa_data.get("id_empresa"),
                ).first()
                
                if existing:
                    for key, value in empresa_data.items():
                        setattr(existing, key, value)
                    results["updated"] += 1
                else:
                    new_empresa = Empresa(**empresa_data)
                    db.add(new_empresa)
                    results["created"] += 1
                    
            except Exception as e:
                results["errors"].append(f"Erro ao processar empresa: {str(e)}")
        
        db.commit()
        return {"status": "success", "results": results}
        
    except IntegrityError as ie:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro de integridade: {str(ie)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar empresa: {str(e)}")


@router.get("/empresa", response_model=Optional[EmpresaOut])
def get_empresa(
    db: Session = Depends(get_db),
):
    empresa = db.query(Empresa).first()
    if not empresa:
        return None
    return empresa


@router.post("/simplesfique/login", response_model=SimpleSfiqueLoginResponse)
async def simplesfique_login(
    body: SimpleSfiqueLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Login API v1 SimpleSfique, persiste sessão e sincroniza empresa."""
    result = await sync_service.login_simplesfique(
        db,
        request,
        email=body.email,
        senha=body.senha,
        os_usuario=body.os_usuario,
        senha_os=body.senha_os,
    )
    return SimpleSfiqueLoginResponse(**result)


@router.get("/sessao", response_model=Optional[SessaoCompletaOut])
def obter_sessao(db: Session = Depends(get_db)):
    return api_session.sessao_to_dict_completa(api_session.get_session(db))


@router.post("/simplesfique/sessao-totem", response_model=SessaoCompletaOut)
def salvar_sessao_totem(
    body: SessaoTotemRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Persiste tokens e credenciais após o login de 3 passos no totem."""
    sessao = api_session.save_terminal_session(
        db,
        jwt_token=body.jwt_token,
        terminal_id=body.terminal_id,
        terminal_token=body.terminal_token,
        senha_terminal=body.senha_terminal,
        email=body.email,
        senha_simples=body.senha_simples,
        id_saas=body.id_saas,
        id_empresa=body.id_empresa,
    )
    request.app.state.external_api_token = sessao.token
    return api_session.sessao_to_dict_completa(sessao)


@router.post("/simplesfique/relogin", response_model=ReloginOut)
async def relogin_simplesfique(
    request: Request,
    db: Session = Depends(get_db),
):
    """Re-autentica no SimplesFique usando credenciais salvas. Chamado automaticamente em 401."""
    from core.credential_crypto import decrypt_secret

    sessao = api_session.get_session(db)
    if not sessao:
        raise HTTPException(status_code=422, detail="Nenhuma sessão configurada")

    if not sessao.email or not sessao.senha_simples_enc:
        raise HTTPException(status_code=422, detail="Credenciais SimplesFique não salvas — refaça o login")

    if not sessao.terminal_id or not sessao.senha_terminal_enc:
        raise HTTPException(status_code=422, detail="Credenciais do terminal não salvas — refaça o login")

    try:
        decrypt_secret(sessao.senha_simples_enc)
        decrypt_secret(sessao.senha_terminal_enc)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Erro ao descriptografar credenciais: {exc}") from exc

    # Renovação mockada — sem SimplesFique real, apenas gera novos tokens válidos
    login_data = mock_data.mock_login_response(sessao.email)
    jwt_token = login_data["token"]
    terminal_token = mock_data.mock_terminal_validar_senha_response(sessao.terminal_id)["access_token"]

    api_session.update_tokens(db, jwt_token=jwt_token, terminal_token=terminal_token)
    request.app.state.external_api_token = jwt_token

    return ReloginOut(jwt_token=jwt_token, terminal_token=terminal_token)


@router.post("/pull/{etapa}")
async def pull_etapa(
    etapa: str,
    request: Request,
    db: Session = Depends(get_db),
):
    return await sync_service.pull_etapa(db, request, etapa)


@router.post("/simplesfique/empresa", response_model=EmpresaOut)
def simplesfique_salvar_empresa(
    data: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
):
    """Persiste a empresa escolhida e atualiza id_empresa na sessão."""
    sessao = api_session.get_session(db)
    if not sessao or not sessao.token:
        raise HTTPException(status_code=503, detail="Faça login no SimpleSfique primeiro")

    id_saas = int(sessao.id_saas)
    id_empresa = int(data.get("id_empresa") or data.get("id") or 0)
    if id_empresa < 1:
        raise HTTPException(status_code=400, detail="id_empresa inválido")

    mapped = sync_service.enrich_empresa_from_session(
        sync_service.map_empresa(data, id_saas, id_empresa),
        sessao,
    )
    results = sync_service.persist_empresas(db, [mapped])
    if results["errors"]:
        raise HTTPException(status_code=400, detail=results["errors"][0])

    sessao.id_empresa = id_empresa
    db.commit()
    api_session.apply_session_to_app(request, sessao)

    empresa = db.query(Empresa).filter(Empresa.id_saas == id_saas).first()
    if not empresa:
        raise HTTPException(status_code=500, detail="Falha ao salvar empresa")
    return empresa


@router.post("/pull/completa")
async def pull_completa(
    request: Request,
    db: Session = Depends(get_db),
):
    """Sincroniza empresa e catálogo completo do SimpleSfique."""
    return await sync_service.pull_completa(request, db)


@router.get("/empresasync")
async def get_empresasync(
    dhsinc: str,
    request: Request,
):
    return await call_external_api(request, "sincempresa", dhsinc)
