from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import httpx
from datetime import datetime

from core.database import get_db
from core.config import URL_API
from models.orm import (

    Empresa, Grupo, Subgrupo, Marca, Medida, Produto, 
    TipoPagamento, Saida
    
)
from models.schemas import (
    EmpresaOut,
    SessaoSimpleSfiqueOut,
    SimpleSfiqueLoginRequest,
    SimpleSfiqueLoginResponse,
)
from services import api_session, sync_service

router = APIRouter(prefix="/sinc", tags=["sincronizacao"])


async def call_external_api(request: Request, endpoint: str, dhsinc: Optional[str] = None):
    """Helper para fazer requisições à API externa sincronizada com token"""
    token = request.app.state.external_api_token
    
    if not token:
        raise HTTPException(status_code=503, detail="Token não disponível")
    
    try:
        # Converte a data para formato datetime do banco de dados se fornecida
        dhsinc_formatted = dhsinc
        if dhsinc:
            if len(dhsinc) == 10:  # "2024-01-01"
                dhsinc_formatted = datetime.strptime(dhsinc, "%Y-%m-%d").strftime("%Y-%m-%d%H:%M:%S")
        
        url = f"{URL_API}/{endpoint}"
        if dhsinc_formatted:
            url += f"/{dhsinc_formatted}"
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            return response.json()
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Formato de data inválido: {str(ve)}")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar: {str(e)}")


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


@router.get("/sessao", response_model=Optional[SessaoSimpleSfiqueOut])
def obter_sessao(db: Session = Depends(get_db)):
    return api_session.sessao_to_dict(api_session.get_session(db))


@router.get("/etapas")
def listar_etapas_sync(db: Session = Depends(get_db)):
    return {"etapas": sync_service.list_etapas(db)}


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


# ── Sincronização de Grupo ────────────────────────────────────────────────────

@router.post("/grupo")
def sinc_grupo(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """Persiste dados de grupo no banco de dados"""
    try:
        if isinstance(data, list):
            grupos = data
        else:
            grupos = [data]
        
        results = {"created": 0, "updated": 0, "errors": []}
        
        for grupo_data in grupos:
            try:
                existing = db.query(Grupo).filter(
                    Grupo.id_grupo == grupo_data.get("id_grupo")
                ).first()
                
                if existing:
                    for key, value in grupo_data.items():
                        setattr(existing, key, value)
                    results["updated"] += 1
                else:
                    new_grupo = Grupo(**grupo_data)
                    db.add(new_grupo)
                    results["created"] += 1
                    
            except Exception as e:
                results["errors"].append(f"Erro ao processar grupo {grupo_data.get('id_grupo')}: {str(e)}")
        
        db.commit()
        return {"status": "success", "results": results}
        
    except IntegrityError as ie:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro de integridade: {str(ie)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar grupo: {str(e)}")


@router.get("/gruposync")
async def get_gruposync(
    dhsinc: str,
    request: Request,
):
    return await call_external_api(request, "sincgrupo", dhsinc)


# ── Sincronização de Marca ────────────────────────────────────────────────────

@router.post("/marca")
def sinc_marca(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """Persiste dados de marca no banco de dados"""
    try:
        if isinstance(data, list):
            marcas = data
        else:
            marcas = [data]
        
        results = {"created": 0, "updated": 0, "errors": []}
        
        for marca_data in marcas:
            try:
                existing = db.query(Marca).filter(
                    Marca.id_marca == marca_data.get("id_marca")
                ).first()
                
                if existing:
                    for key, value in marca_data.items():
                        setattr(existing, key, value)
                    results["updated"] += 1
                else:
                    new_marca = Marca(**marca_data)
                    db.add(new_marca)
                    results["created"] += 1
                    
            except Exception as e:
                results["errors"].append(f"Erro ao processar marca {marca_data.get('id_marca')}: {str(e)}")
        
        db.commit()
        return {"status": "success", "results": results}
        
    except IntegrityError as ie:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro de integridade: {str(ie)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar marca: {str(e)}")


@router.get("/marcasync")
async def get_marcasync(
    dhsinc: str,
    request: Request,
):
    return await call_external_api(request, "sincmarca", dhsinc)


# ── Sincronização de Medida ───────────────────────────────────────────────────

@router.post("/medida")
def sinc_medida(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """Persiste dados de medida no banco de dados"""
    try:
        if isinstance(data, list):
            medidas = data
        else:
            medidas = [data]
        
        results = {"created": 0, "updated": 0, "errors": []}
        
        for medida_data in medidas:
            try:
                existing = db.query(Medida).filter(
                    Medida.id_medida == medida_data.get("id_medida")
                ).first()
                
                if existing:
                    for key, value in medida_data.items():
                        setattr(existing, key, value)
                    results["updated"] += 1
                else:
                    new_medida = Medida(**medida_data)
                    db.add(new_medida)
                    results["created"] += 1
                    
            except Exception as e:
                results["errors"].append(f"Erro ao processar medida {medida_data.get('id_medida')}: {str(e)}")
        
        db.commit()
        return {"status": "success", "results": results}
        
    except IntegrityError as ie:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro de integridade: {str(ie)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar medida: {str(e)}")


@router.get("/medidasync")
async def get_medidasync(
    dhsinc: str,
    request: Request,
):
    return await call_external_api(request, "sincmedida", dhsinc)


# ── Sincronização de Produto ──────────────────────────────────────────────────

@router.post("/produto")
def sinc_produto(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """Persiste dados de produto no banco de dados"""
    try:
        if isinstance(data, list):
            produtos = data
        else:
            produtos = [data]
        
        results = {"created": 0, "updated": 0, "errors": []}
        
        for produto_data in produtos:
            try:
                existing = db.query(Produto).filter(
                    Produto.id_produto == produto_data.get("id_produto")
                ).first()
                
                if existing:
                    for key, value in produto_data.items():
                        setattr(existing, key, value)
                    results["updated"] += 1
                else:
                    new_produto = Produto(**produto_data)
                    db.add(new_produto)
                    results["created"] += 1
                    
            except Exception as e:
                results["errors"].append(f"Erro ao processar produto {produto_data.get('id_produto')}: {str(e)}")
        
        db.commit()
        return {"status": "success", "results": results}
        
    except IntegrityError as ie:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro de integridade: {str(ie)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar produto: {str(e)}")


@router.get("/produtosync")
async def get_produtosync(
    dhsinc: str,
    request: Request,
):
    return await call_external_api(request, "sincproduto", dhsinc)


# ── Sincronização de Subgrupo ─────────────────────────────────────────────────

@router.post("/subgrupo")
def sinc_subgrupo(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """Persiste dados de subgrupo no banco de dados"""
    try:
        if isinstance(data, list):
            subgrupos = data
        else:
            subgrupos = [data]
        
        results = {"created": 0, "updated": 0, "errors": []}
        
        for subgrupo_data in subgrupos:
            try:
                existing = db.query(Subgrupo).filter(
                    (Subgrupo.id_grupo == subgrupo_data.get("id_grupo")) &
                    (Subgrupo.id_subgrupo == subgrupo_data.get("id_subgrupo"))
                ).first()
                
                if existing:
                    for key, value in subgrupo_data.items():
                        setattr(existing, key, value)
                    results["updated"] += 1
                else:
                    new_subgrupo = Subgrupo(**subgrupo_data)
                    db.add(new_subgrupo)
                    results["created"] += 1
                    
            except Exception as e:
                results["errors"].append(f"Erro ao processar subgrupo: {str(e)}")
        
        db.commit()
        return {"status": "success", "results": results}
        
    except IntegrityError as ie:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro de integridade: {str(ie)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar subgrupo: {str(e)}")


@router.get("/subgruposync")
async def get_subgruposync(
    dhsinc: str,
    request: Request,
):
    return await call_external_api(request, "sincsubgrupo", dhsinc)


# ── Sincronização de Tipo de Pagrecio ────────────────────────────────────────

@router.post("/tipopagrecio")
def sinc_tipopagrecio(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """Persiste dados de tipo de pagamento/recebimento no banco de dados"""
    try:
        if isinstance(data, list):
            tipos = data
        else:
            tipos = [data]
        
        results = {"created": 0, "updated": 0, "errors": []}
        
        for tipo_data in tipos:
            try:
                existing = db.query(TipoPagamento).filter(
                    TipoPagamento.id == tipo_data.get("id")
                ).first()
                
                if existing:
                    for key, value in tipo_data.items():
                        setattr(existing, key, value)
                    results["updated"] += 1
                else:
                    new_tipo = TipoPagamento(**tipo_data)
                    db.add(new_tipo)
                    results["created"] += 1
                    
            except Exception as e:
                results["errors"].append(f"Erro ao processar tipo {tipo_data.get('id')}: {str(e)}")
        
        db.commit()
        return {"status": "success", "results": results}
        
    except IntegrityError as ie:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro de integridade: {str(ie)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar tipo de pagamento: {str(e)}")


@router.get("/tipopagrecsync")
async def get_tipopagrecsync(request: Request):
    return await call_external_api(request, "sinctipopagrec")


# ── Sincronização de Venda Ambiente ───────────────────────────────────────────

@router.post("/venambiente")
def sinc_venambiente(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """Persiste dados de venda ambiente no banco de dados"""
    try:
        if isinstance(data, list):
            vendas = data
        else:
            vendas = [data]
        
        results = {"created": 0, "updated": 0, "errors": []}
        
        for venda_data in vendas:
            try:
                existing = db.query(Saida).filter(
                    Saida.id == venda_data.get("id")
                ).first()
                
                if existing:
                    for key, value in venda_data.items():
                        setattr(existing, key, value)
                    results["updated"] += 1
                else:
                    new_venda = Saida(**venda_data)
                    db.add(new_venda)
                    results["created"] += 1
                    
            except Exception as e:
                results["errors"].append(f"Erro ao processar venda ambiente: {str(e)}")
        
        db.commit()
        return {"status": "success", "results": results}
        
    except IntegrityError as ie:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro de integridade: {str(ie)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar venda ambiente: {str(e)}")


@router.get("/venambientsync")
async def get_venambientsync(
    dhsinc: str,
    request: Request,
):
    return await call_external_api(request, "sincvenambiente", dhsinc)


# ── Sincronização de Venda Painel ────────────────────────────────────────────

@router.post("/venpainel")
def sinc_venpainel(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """Persiste dados de venda painel no banco de dados"""
    try:
        if isinstance(data, list):
            vendas = data
        else:
            vendas = [data]
        
        results = {"created": 0, "updated": 0, "errors": []}
        
        for venda_data in vendas:
            try:
                existing = db.query(Saida).filter(
                    Saida.id == venda_data.get("id")
                ).first()
                
                if existing:
                    for key, value in venda_data.items():
                        setattr(existing, key, value)
                    results["updated"] += 1
                else:
                    new_venda = Saida(**venda_data)
                    db.add(new_venda)
                    results["created"] += 1
                    
            except Exception as e:
                results["errors"].append(f"Erro ao processar venda painel: {str(e)}")
        
        db.commit()
        return {"status": "success", "results": results}
        
    except IntegrityError as ie:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro de integridade: {str(ie)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar venda painel: {str(e)}")


@router.get("/venpainelsync")
async def get_venpainelsync(
    dhsinc: str,
    request: Request,
):
    return await call_external_api(request, "sincvenpainel", dhsinc)


# ── Sincronização de Venda Terminal ──────────────────────────────────────────

@router.post("/venterminal")
def sinc_venterminal(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """Persiste dados de venda terminal no banco de dados"""
    try:
        if isinstance(data, list):
            vendas = data
        else:
            vendas = [data]
        
        results = {"created": 0, "updated": 0, "errors": []}
        
        for venda_data in vendas:
            try:
                existing = db.query(Saida).filter(
                    Saida.id == venda_data.get("id")
                ).first()
                
                if existing:
                    for key, value in venda_data.items():
                        setattr(existing, key, value)
                    results["updated"] += 1
                else:
                    new_venda = Saida(**venda_data)
                    db.add(new_venda)
                    results["created"] += 1
                    
            except Exception as e:
                results["errors"].append(f"Erro ao processar venda terminal: {str(e)}")
        
        db.commit()
        return {"status": "success", "results": results}
        
    except IntegrityError as ie:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro de integridade: {str(ie)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar venda terminal: {str(e)}")


@router.get("/venterminalsync")
async def get_venterminalsync(
    dhsinc: str,
    request: Request,
):
    return await call_external_api(request, "sincventerminal", dhsinc)
