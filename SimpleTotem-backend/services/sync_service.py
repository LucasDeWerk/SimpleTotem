import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import httpx
from fastapi import HTTPException, Request
from jose import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.config import api_v1_url
from models.orm import (
    Empresa,
    Grupo,
    Marca,
    Medida,
    Produto,
    Subgrupo,
    SyncCheckpoint,
    TipoPagamento,
)
from services import api_session
from services.empresa_credentials import apply_credentials

logger = logging.getLogger(__name__)

DHSINC_INICIAL = "1970-01-01 00:00:00"

SYNC_STEPS: List[Dict[str, Any]] = [
    {"id": "empresas", "label": "Empresas", "path": "empresas", "dhsinc": True, "id_saas": True},
    {"id": "grupos", "label": "Grupos", "path": "grupos", "dhsinc": True, "id_saas": True},
    {"id": "subgrupos", "label": "Subgrupos", "path": "subgrupos", "dhsinc": True, "id_saas": True},
    {"id": "marcas", "label": "Marcas", "path": "marcas", "dhsinc": True, "id_saas": True},
    {"id": "medidas", "label": "Medidas", "path": "medidas", "dhsinc": True, "id_saas": False},
    {"id": "tipos-pag-rec", "label": "Tipos de pagamento", "path": "tipos-pag-rec", "dhsinc": False, "id_saas": False},
    {"id": "produtos", "label": "Produtos", "path": "produtos", "dhsinc": True, "id_saas": True, "idempresa": True},
    {"id": "terminais", "label": "Terminais", "path": "terminais", "dhsinc": True, "id_saas": True},
    {"id": "paineis", "label": "Painéis", "path": "paineis", "dhsinc": True, "id_saas": True},
    {"id": "ambientes", "label": "Ambientes", "path": "ambientes", "dhsinc": True, "id_saas": True},
]


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _model_fields(model) -> set:
    return {c.name for c in model.__table__.columns}


def _filter_fields(model, data: Dict[str, Any]) -> Dict[str, Any]:
    allowed = _model_fields(model)
    return {k: v for k, v in data.items() if k in allowed}


def _num(value: Any, default: float = 0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def _session_ids(request: Request) -> tuple[int, int]:
    id_saas = getattr(request.app.state, "id_saas", None)
    id_empresa = getattr(request.app.state, "id_empresa", None)
    if not id_saas or not id_empresa:
        raise HTTPException(status_code=503, detail="Sessão SimpleSfique incompleta. Faça login.")
    return int(id_saas), int(id_empresa)


def _get_token(request: Request) -> str:
    token = getattr(request.app.state, "external_api_token", None)
    if not token:
        raise HTTPException(status_code=503, detail="Token SimpleSfique não disponível. Faça login.")
    return token


def get_checkpoint(db: Session, etapa: str) -> str:
    row = db.query(SyncCheckpoint).filter(SyncCheckpoint.etapa == etapa).first()
    return row.dhsinc if row and row.dhsinc else DHSINC_INICIAL


def save_checkpoint(db: Session, etapa: str, records: int) -> str:
    dhsinc = _now_str()
    row = db.query(SyncCheckpoint).filter(SyncCheckpoint.etapa == etapa).first()
    if not row:
        row = SyncCheckpoint(etapa=etapa)
        db.add(row)
    row.dhsinc = dhsinc
    row.ultimo_records = records
    row.dh_sync = dhsinc
    db.commit()
    return dhsinc



def extract_data(payload: Any) -> List[Dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, dict):
        if "data" in payload:
            data = payload["data"]
            return data if isinstance(data, list) else [data]
        return [payload]
    if isinstance(payload, list):
        return payload
    return []


async def fetch_delta(
    request: Request,
    path: str,
    *,
    dhsinc: Optional[str] = None,
    id_saas: bool = False,
    idempresa: bool = False,
) -> Any:
    token = _get_token(request)
    params: Dict[str, Any] = {}
    if id_saas:
        saas, empresa = _session_ids(request)
        params["id_saas"] = saas
    if idempresa:
        _, empresa = _session_ids(request)
        params["idempresa"] = empresa

    if dhsinc:
        dhsinc_enc = quote(dhsinc, safe="")
        url = api_v1_url(f"sinc/{path}/{dhsinc_enc}")
    else:
        url = api_v1_url(f"sinc/{path}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                params=params or None,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
                timeout=60.0,
            )
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="Token SimpleSfique expirado. Faça login novamente.")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar {path}: {exc}") from exc


def _normalize_dhinc(value: Any) -> str:
    if not value:
        return datetime.now().strftime("%Y-%m-%d")
    raw = str(value).strip()
    if "T" in raw:
        return raw.split("T")[0][:10]
    return raw[:10]


def _apply_session_creds(empresa_data: Dict[str, Any], sessao) -> None:
    pending = api_session.pending_credentials(sessao)
    if pending.get("email_simples"):
        empresa_data["email_simples"] = pending["email_simples"]
    if pending.get("senha_simples_enc"):
        empresa_data["senha_simples"] = pending["senha_simples_enc"]
    if pending.get("usuario_os"):
        empresa_data["usuario_os"] = pending["usuario_os"]
    if pending.get("senha_os_enc"):
        empresa_data["senha_os"] = pending["senha_os_enc"]


def map_empresa(
    item: Dict[str, Any],
    id_saas: int,
    id_empresa: int,
    *,
    email_simples: Optional[str] = None,
    senha_simples: Optional[str] = None,
    usuario_os: Optional[str] = None,
    senha_os: Optional[str] = None,
) -> Dict[str, Any]:
    emp_id = item.get("id_empresa") or item.get("id") or id_empresa
    razao = (item.get("razao_social") or "").strip() or "Empresa"
    nome = (item.get("nome_fantasia") or "").strip() or razao
    mapped = _filter_fields(Empresa, {
        "id_saas": id_saas,
        "id_empresa": int(emp_id),
        "razao_social": razao,
        "nome_fantasia": nome,
        "cpf_cnpj": item.get("cpf_cnpj"),
        "whatsapp": item.get("whatsapp"),
        "integrado_simplesfique": item.get("integrado_simplesfique") or "S",
        "dhinc": _normalize_dhinc(item.get("dhinc")),
        "endereco": item.get("endereco"),
        "numero": item.get("numero"),
        "cep": item.get("cep"),
        "cidade": item.get("cidade"),
        "id_uf": item.get("id_uf"),
        "id_ibge": item.get("id_ibge"),
        "id_bairro": item.get("id_bairro"),
        "bairro": item.get("bairro"),
        "perfil": item.get("perfil"),
        "crt": item.get("crt"),
        "ind_tp_ativ": item.get("ind_tp_ativ"),
        "cnae": item.get("cnae"),
        "ret": item.get("ret"),
        "token": item.get("token"),
        "insc_estadual": item.get("insc_estadual"),
    })
    return apply_credentials(
        mapped,
        email_simples=email_simples,
        senha_simples=senha_simples,
        usuario_os=usuario_os,
        senha_os=senha_os,
    )


def enrich_empresa_from_session(empresa_data: Dict[str, Any], sessao) -> Dict[str, Any]:
    _apply_session_creds(empresa_data, sessao)
    return empresa_data


def attach_session_creds_to_empresa(db: Session, id_saas: int, sessao) -> Optional[Empresa]:
    empresa = db.query(Empresa).filter(Empresa.id_saas == id_saas).first()
    if not empresa or not sessao:
        return empresa
    patch: Dict[str, Any] = {}
    _apply_session_creds(patch, sessao)
    for key, value in patch.items():
        if value:
            setattr(empresa, key, value)
    db.commit()
    db.refresh(empresa)
    return empresa


def map_grupo(item: Dict[str, Any]) -> Dict[str, Any]:
    return _filter_fields(Grupo, {
        "id_grupo": item.get("id_grupo") or item.get("id"),
        "descgrupo": _text(item.get("descgrupo"), "Grupo"),
        "foto": item.get("foto") or b"",
    })


def map_subgrupo(item: Dict[str, Any]) -> Dict[str, Any]:
    mapped = dict(item)
    if "id" in mapped and "id_subgrupo" not in mapped:
        mapped["id_subgrupo"] = mapped.pop("id")
    mapped["descsubgrupo"] = _text(mapped.get("descsubgrupo"), "Subgrupo")
    return _filter_fields(Subgrupo, mapped)


def map_marca(item: Dict[str, Any]) -> Dict[str, Any]:
    return _filter_fields(Marca, {
        "id_marca": item.get("id_marca") or item.get("id"),
        "descmarca": _text(item.get("descmarca"), "Marca"),
    })


def map_medida(item: Dict[str, Any]) -> Dict[str, Any]:
    abrev = _text(item.get("abreviatura"), "UN")
    return _filter_fields(Medida, {
        "id_medida": item.get("id_medida") or item.get("id"),
        "descmedida": _text(item.get("descmedida"), "Unidade"),
        "abreviatura": abrev[:3] if abrev else "UN",
    })


def map_produto(item: Dict[str, Any]) -> Dict[str, Any]:
    custo_compra = _num(item.get("custo_compra"))
    custo_medio = _num(item.get("custo_medio"), custo_compra)
    custo_aquisicao = _num(
        item.get("custo_aquisicao"),
        custo_compra if custo_compra else custo_medio,
    )
    return _filter_fields(Produto, {
        "id_produto": item.get("id_produto") or item.get("id"),
        "descproduto": _text(item.get("descproduto"), "Produto"),
        "gtin": item.get("codigo_gtin") or item.get("gtin"),
        "cod_referencia": item.get("codigo_ref") or item.get("codigo_sku"),
        "cod_fabricacao": item.get("codigo_fab"),
        "id_grupo": _int(item.get("id_grupo")),
        "id_subgrupo": _int(item.get("id_subgrupo")),
        "id_marca": _int(item.get("id_marca")),
        "id_medida": _int(item.get("id_medida")),
        "id_ncm": item.get("id_ncm"),
        "peso": _num(item.get("peso")),
        "custo_compra": custo_compra,
        "custo_medio": custo_medio,
        "custo_aquisicao": custo_aquisicao,
        "preco_venda": _num(item.get("preco_venda")),
        "foto": item.get("foto") or b"",
        "estoque": _num(item.get("estoque")),
        "dhinc": _normalize_dhinc(item.get("dhinc")),
    })


def map_tipo_pag(item: Dict[str, Any]) -> Dict[str, Any]:
    tipo_id = item.get("id") or item.get("id_tipo_pagamento") or item.get("codigo")
    descricao = (
        item.get("desctipopagrec")
        or item.get("descricao")
        or item.get("desc")
        or item.get("nome")
        or (f"Pagamento {tipo_id}" if tipo_id is not None else "Pagamento")
    )
    id_str = str(tipo_id).strip() if tipo_id is not None else ""
    return _filter_fields(TipoPagamento, {
        "id": id_str,
        "desctipopagrec": _text(descricao, "Pagamento"),
    })


def persist_empresas(db: Session, empresas: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = {"created": 0, "updated": 0, "errors": []}
    for empresa_data in empresas:
        try:
            id_saas = empresa_data.get("id_saas")
            id_empresa = empresa_data.get("id_empresa")
            if not id_saas or not id_empresa:
                results["errors"].append("Registro de empresa sem id_saas ou id_empresa")
                continue
            existing = db.query(Empresa).filter(
                Empresa.id_saas == id_saas,
                Empresa.id_empresa == id_empresa,
            ).first()
            if existing:
                for key, value in empresa_data.items():
                    if value is not None:
                        setattr(existing, key, value)
                results["updated"] += 1
            else:
                db.add(Empresa(**empresa_data))
                results["created"] += 1
        except Exception as exc:
            results["errors"].append(f"Erro ao processar empresa: {exc}")
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro de integridade: {exc}") from exc
    return results


def _persist_by_key(db: Session, model, items: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    results = {"created": 0, "updated": 0, "errors": []}
    for item in items:
        try:
            filtered = _filter_fields(model, item)
            pk = filtered.get(key)
            if pk is None or pk == "":
                results["errors"].append(f"Registro sem {key}")
                continue
            existing = db.query(model).filter(getattr(model, key) == pk).first()
            if existing:
                for k, v in filtered.items():
                    if v is not None:
                        setattr(existing, k, v)
                results["updated"] += 1
            else:
                db.add(model(**filtered))
                results["created"] += 1
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            results["errors"].append(str(exc))
        except Exception as exc:
            db.rollback()
            results["errors"].append(str(exc))
    return results


def persist_subgrupos(db: Session, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    results = {"created": 0, "updated": 0, "errors": []}
    for item in items:
        try:
            filtered = map_subgrupo(item)
            existing = db.query(Subgrupo).filter(
                Subgrupo.id_grupo == filtered.get("id_grupo"),
                Subgrupo.id_subgrupo == filtered.get("id_subgrupo"),
            ).first()
            if existing:
                for fld, value in filtered.items():
                    if value is not None:
                        setattr(existing, fld, value)
                results["updated"] += 1
            else:
                db.add(Subgrupo(**filtered))
                results["created"] += 1
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            results["errors"].append(str(exc))
        except Exception as exc:
            db.rollback()
            results["errors"].append(str(exc))
    return results


async def pull_etapa(db: Session, request: Request, etapa_id: str) -> Dict[str, Any]:
    step = next((s for s in SYNC_STEPS if s["id"] == etapa_id), None)
    if not step:
        raise HTTPException(status_code=404, detail=f"Etapa desconhecida: {etapa_id}")

    dhsinc = get_checkpoint(db, etapa_id) if step.get("dhsinc") else None
    raw = await fetch_delta(
        request,
        step["path"],
        dhsinc=dhsinc,
        id_saas=step.get("id_saas", False),
        idempresa=step.get("idempresa", False),
    )

    records = 0
    persist_result: Dict[str, Any] = {"created": 0, "updated": 0, "errors": []}

    if etapa_id == "ambientes":
        records = int(raw.get("records", 0)) if isinstance(raw, dict) else len(extract_data(raw))
    elif etapa_id in ("terminais", "paineis"):
        items = extract_data(raw)
        records = int(raw.get("records", len(items))) if isinstance(raw, dict) else len(items)
    else:
        items = extract_data(raw)
        records = int(raw.get("records", len(items))) if isinstance(raw, dict) else len(items)
        id_saas, id_empresa = _session_ids(request)

        if etapa_id == "empresas":
            sessao = api_session.get_session(db)
            mapped = []
            for i in items:
                emp_id = id_empresa or i.get("id_empresa") or i.get("id")
                if not emp_id:
                    continue
                mapped.append(
                    enrich_empresa_from_session(
                        map_empresa(i, id_saas, int(emp_id)),
                        sessao,
                    )
                )
            persist_result = persist_empresas(db, mapped)
        elif etapa_id == "grupos":
            persist_result = _persist_by_key(db, Grupo, [map_grupo(i) for i in items], "id_grupo")
        elif etapa_id == "subgrupos":
            persist_result = persist_subgrupos(db, items)
        elif etapa_id == "marcas":
            persist_result = _persist_by_key(db, Marca, [map_marca(i) for i in items], "id_marca")
        elif etapa_id == "medidas":
            persist_result = _persist_by_key(db, Medida, [map_medida(i) for i in items], "id_medida")
        elif etapa_id == "tipos-pag-rec":
            persist_result = _persist_by_key(
                db, TipoPagamento, [map_tipo_pag(i) for i in items], "id"
            )
        elif etapa_id == "produtos":
            persist_result = _persist_by_key(
                db, Produto, [map_produto(i) for i in items], "id_produto"
            )

    synced_records = records
    if persist_result:
        persisted = (persist_result.get("created") or 0) + (persist_result.get("updated") or 0)
        if persisted > 0:
            synced_records = persisted
    save_checkpoint(db, etapa_id, synced_records)

    return {
        "etapa": etapa_id,
        "records": records,
        "dhsinc_usado": dhsinc,
        "persist": persist_result,
    }


async def pull_completa(db: Session, request: Request) -> Dict[str, Any]:
    etapas: Dict[str, Any] = {}
    erros: List[str] = []
    for step in SYNC_STEPS:
        try:
            etapas[step["id"]] = await pull_etapa(db, request, step["id"])
        except HTTPException:
            raise
        except Exception as exc:
            erros.append(f"{step['id']}: {exc}")
    return {"status": "success" if not erros else "partial", "etapas": etapas, "errors": erros}


def _claims_from_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.get_unverified_claims(token)
    except Exception:
        return {}


def _resolve_login_context(data: Dict[str, Any], token: str) -> Tuple[Optional[int], Optional[int], List[Dict[str, Any]]]:
    """Extrai id_saas, id_empresa e lista de empresas da resposta de login."""
    empresas = data.get("empresas") or []
    saas = data.get("saas") or {}
    usuario = data.get("usuario") or {}
    claims = _claims_from_token(token)

    id_saas = (
        saas.get("id_saas")
        or saas.get("id")
        or usuario.get("id_saas")
        or claims.get("id_saas")
        or (empresas[0].get("id_saas") if empresas else None)
    )

    id_empresa = (
        usuario.get("id_empresa")
        or claims.get("id_empresa")
    )
    if not id_empresa and len(empresas) == 1:
        id_empresa = empresas[0].get("id_empresa") or empresas[0].get("id")

    return id_saas, id_empresa, empresas


async def login_simplesfique(
    db: Session,
    request: Request,
    *,
    email: str,
    senha: str,
    os_usuario: Optional[str] = None,
    senha_os: Optional[str] = None,
) -> Dict[str, Any]:
    email = (email or "").strip()
    if not email or not senha:
        raise HTTPException(status_code=400, detail="Email e senha são obrigatórios")

    url = api_v1_url("auth/login")
    logger.info("Login SimpleSfique: POST %s", url)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={"email": email, "senha": senha},
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=30.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Não foi possível conectar ao SimpleSfique: {exc}") from exc

    if response.status_code == 401:
        detail = response.json().get("erro", "Credenciais inválidas") if response.content else "Credenciais inválidas"
        raise HTTPException(status_code=401, detail=detail)
    if response.status_code == 403:
        detail = response.json().get("erro", "Acesso negado para esta empresa") if response.content else "Acesso negado"
        raise HTTPException(status_code=403, detail=detail)
    if response.status_code >= 400:
        try:
            body = response.json()
            detail = body.get("erro") or body.get("detail") or response.text
        except Exception:
            detail = response.text
        raise HTTPException(status_code=response.status_code, detail=detail)

    data = response.json()
    token = data.get("token")
    if not token:
        raise HTTPException(status_code=502, detail="Resposta de login sem token")

    id_saas, id_empresa, empresas_login = _resolve_login_context(data, token)
    if not id_saas:
        raise HTTPException(status_code=502, detail="Resposta de login sem id_saas")

    sessao = api_session.save_session(
        db,
        token=token,
        id_saas=int(id_saas),
        id_empresa=int(id_empresa or 0),
        email=email,
        os_usuario=os_usuario,
        senha_simples=senha,
        senha_os=senha_os,
        expira_em=data.get("expira_em"),
    )
    api_session.apply_session_to_app(request, sessao)

    if len(empresas_login) > 1 and not id_empresa:
        return {
            "token_ok": True,
            "requires_selection": True,
            "expira_em": data.get("expira_em"),
            "tipo_token": data.get("tipo_token", "bearer"),
            "sessao": api_session.sessao_to_dict(sessao),
            "empresa": None,
            "empresas": empresas_login,
            "usuario": data.get("usuario"),
            "saas": data.get("saas"),
        }

    if not id_empresa and empresas_login:
        id_empresa = empresas_login[0].get("id_empresa") or empresas_login[0].get("id")
    if not id_empresa:
        await pull_etapa(db, request, "empresas")
        empresa_db = attach_session_creds_to_empresa(db, int(id_saas), sessao)
        if not empresa_db:
            empresa_db = db.query(Empresa).filter(Empresa.id_saas == int(id_saas)).first()
    else:
        id_empresa = int(id_empresa)
        sessao.id_empresa = id_empresa
        request.app.state.id_empresa = id_empresa
        db.commit()

        empresa_alvo = None
        creds = {
            "email_simples": email,
            "senha_simples": senha,
            "usuario_os": os_usuario,
            "senha_os": senha_os,
        }
        for item in empresas_login:
            emp_id = item.get("id_empresa") or item.get("id")
            if emp_id == id_empresa:
                empresa_alvo = map_empresa(item, int(id_saas), id_empresa, **creds)
                break
        if not empresa_alvo and empresas_login:
            empresa_alvo = map_empresa(empresas_login[0], int(id_saas), id_empresa, **creds)

        if empresa_alvo:
            persist_empresas(db, [empresa_alvo])
        else:
            await pull_etapa(db, request, "empresas")

        empresa_db = db.query(Empresa).filter(Empresa.id_saas == int(id_saas)).first()

    if not empresa_db:
        raise HTTPException(status_code=500, detail="Empresa não foi salva após login")

    return {
        "token_ok": True,
        "requires_selection": False,
        "expira_em": data.get("expira_em"),
        "tipo_token": data.get("tipo_token", "bearer"),
        "sessao": api_session.sessao_to_dict(sessao),
        "empresa": empresa_db,
        "empresas": [empresa_db],
        "usuario": data.get("usuario"),
        "saas": data.get("saas"),
    }
