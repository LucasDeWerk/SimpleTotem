"""Funções administrativas/de teste CliSiTef exigidas pelo Roteiro de
Pré-Homologação Fiserv (Menu Administrativo 110 e, se necessário, outras
funções via código livre), rodadas de forma interativa a partir do painel
admin — mesmo padrão do cancelamento interativo, protegido por autenticação
admin (get_current_admin), igual aos demais endpoints administrativos."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_admin
from models.orm import Empresa
from models.schemas import IniciarFuncaoAdminRequest, ResponderPromptRequest
from services import sitef_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/homologacao", tags=["homologacao"])


@router.post("/funcao-admin/iniciar")
def iniciar_funcao_admin(
    body: IniciarFuncaoAdminRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    # Mesmo padrão de /vendas/iniciatransacao: CNPJ do estabelecimento vem da
    # própria empresa cadastrada no banco local, não é responsabilidade do
    # frontend informá-lo.
    cnpj_estabelecimento = body.cnpj_estabelecimento
    if not cnpj_estabelecimento:
        empresa = db.query(Empresa).first()
        cnpj_estabelecimento = (empresa.cpf_cnpj or "") if empresa else ""

    try:
        execucao_id = sitef_service.iniciar_funcao_administrativa_async(
            funcao_codigo=body.funcao_codigo,
            cnpj_estabelecimento=cnpj_estabelecimento,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    return {"execucao_id": execucao_id}


@router.get("/funcao-admin/{execucao_id}/status")
def status_funcao_admin(
    execucao_id: str,
    _: dict = Depends(get_current_admin),
):
    estado = sitef_service.obter_status_funcao_admin(execucao_id)
    if not estado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execução não encontrada")
    return estado


@router.post("/funcao-admin/{execucao_id}/responder")
def responder_funcao_admin(
    execucao_id: str,
    body: ResponderPromptRequest,
    _: dict = Depends(get_current_admin),
):
    try:
        sitef_service.responder_prompt_funcao_admin(execucao_id, body.valor)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return {"ok": True}
