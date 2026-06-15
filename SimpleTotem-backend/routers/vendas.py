import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.orm import Saida, SaidaItem, TipoPagamento, Empresa
from models.schemas import (
    SaidaOut, SaidaItemOut, TipoPagamentoOut, MetodoPagamentoOut,
    IniciaVendaRequest, IniciaVendaResponse, ItemVendaCalculado,
    IniciaTransacaoRequest, IniciaTransacaoStartResponse, TransacaoStatusResponse,
)
from services import sitef_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vendas", tags=["vendas"])

# ─── Métodos de pagamento ────────────────────────────────────────────────────

@router.get("/metodos-pagamento", response_model=List[MetodoPagamentoOut])
def list_metodos_pagamento(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """Retorna os métodos de pagamento cadastrados em tfin_tipopagrec."""
    tipos = db.query(TipoPagamento).order_by(TipoPagamento.desctipopagrec).all()
    return [
        MetodoPagamentoOut(
            type=str(t.id),
            label=t.desctipopagrec or str(t.id),
            icon="",
            available=True,
        )
        for t in tipos
    ]


# ─── Inicia Venda — cálculo do total ─────────────────────────────────────────

@router.post("/iniciavenda", response_model=IniciaVendaResponse)
def inicia_venda(
    req: IniciaVendaRequest,
    _: str = Depends(get_current_user),
):
    """
    Calcula o total da venda a partir dos itens recebidos.
    No futuro, calculará tributos e devoluções fiscais.
    Não grava nada no banco de dados ainda.
    """
    itens_calculados = []
    for item in req.itens:
        total_item = round(item.quantidade * item.preco_unitario, 2)
        itens_calculados.append(
            ItemVendaCalculado(
                produto_id=item.produto_id,
                descricao=item.descricao,
                quantidade=item.quantidade,
                preco_unitario=item.preco_unitario,
                total_item=total_item,
            )
        )

    subtotal = round(sum(i.total_item for i in itens_calculados), 2)
    desconto = 0.0  # futuro: calcular descontos/promoções
    total    = round(subtotal - desconto, 2)

    return IniciaVendaResponse(
        subtotal=subtotal,
        desconto=desconto,
        total=total,
        itens=itens_calculados,
    )


# ─── Inicia Transação — SiTef + gravação + impressão ─────────────────────────

@router.post("/iniciatransacao", response_model=IniciaTransacaoStartResponse)
def inicia_transacao(
    req: IniciaTransacaoRequest,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """
    Inicia transação SiTef (cartão ou PIX) em background.
    O frontend deve consultar GET /vendas/transacao/{id} para QR Code e status.
    """
    # 1. Re-calcular total
    total_recalculado = round(
        sum(i.quantidade * i.preco_unitario for i in req.itens), 2
    )

    logger.info(
        "[Transacao] itens recebidos: %s",
        [(i.produto_id, i.quantidade, i.preco_unitario) for i in req.itens]
    )
    logger.info(
        "[Transacao] total_cliente=%.4f total_recalculado=%.4f",
        req.total_cliente, total_recalculado,
    )
    # 2. Definir total autoritativo
    if abs(total_recalculado - req.total_cliente) < 0.01:
        total_final = req.total_cliente
    else:
        logger.warning(
            "[Transacao] Divergência de total: cliente=%.2f recalculado=%.2f — usando recalculado",
            req.total_cliente, total_recalculado,
        )
        total_final = total_recalculado

    # Converter para centavos (SiTef espera inteiro em centavos)
    valor_centavos = int(round(total_final * 100))

    # 3. Cupom fiscal único (AAAAMMDDHHMMSS — exigência PIX/homologação)
    cupom = req.cupom or datetime.now().strftime("%Y%m%d%H%M%S")

    # 4. CNPJ do estabelecimento para ConfiguraIntSiTefInterativoEx
    empresa = db.query(Empresa).first()
    cnpj_estabelecimento = (empresa.cpf_cnpj or "") if empresa else ""

    # 5. Mapear método de pagamento para código SiTef
    # Busca a descrição no banco para fazer o mapeamento correto
    tipo_pag = db.query(TipoPagamento).filter(
        TipoPagamento.id == int(req.metodo_pagamento_id)
    ).first() if req.metodo_pagamento_id.isdigit() else None
    descricao_pag = (tipo_pag.desctipopagrec or "") if tipo_pag else req.metodo_pagamento_id
    funcao_sitef = _metodo_para_funcao(descricao_pag)
    logger.info("[Transacao] funcao_sitef=%d desc=%s cupom=%s", funcao_sitef, descricao_pag, cupom)

    try:
        transacao_id = sitef_service.iniciar_transacao_async(
            funcao=funcao_sitef,
            valor_centavos=valor_centavos,
            cupom=cupom,
            cnpj_estabelecimento=cnpj_estabelecimento,
            total_cobrado=total_final,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"CliSiTef não disponível: {exc}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )

    return IniciaTransacaoStartResponse(transacao_id=transacao_id, status="processando")


@router.get("/transacao/{transacao_id}", response_model=TransacaoStatusResponse)
def status_transacao(
    transacao_id: str,
    _: str = Depends(get_current_user),
):
    """Status em tempo real — mensagens CliSiTef, QR Code PIX e resultado final."""
    data = sitef_service.obter_status_transacao(transacao_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transação não encontrada")
    return TransacaoStatusResponse(**data)


def _metodo_para_funcao(metodo_id: str) -> int:
    """
    Mapeia o id de tfin_tipopagrec para o código de função SiTef.
    Por padrão usa 0 (menu geral) — o cliente escolhe no pinpad.
    Ajuste conforme os IDs do seu banco de dados.
    """
    m = (metodo_id or "").lower()
    if "cred" in m:
        return 2  # Crédito
    if "deb" in m:
        return 3  # Débito
    if "voucher" in m or "beneficio" in m or "bene" in m:
        return 4
    if "pix" in m or "carteira" in m or "digital" in m or "qr" in m:
        return 122  # Carteira Digital — Venda (PIX)
    return 0  # Menu geral


# ─── Listagem de vendas ───────────────────────────────────────────────────────

@router.get("", response_model=List[SaidaOut])
def list_vendas(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    return db.query(Saida).order_by(Saida.id.desc()).all()


@router.get("/{id_venda}", response_model=SaidaOut)
def get_venda(
    id_venda: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    venda = db.query(Saida).filter(Saida.id == id_venda).first()
    if not venda:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venda não encontrada")
    return venda


@router.get("/{id_venda}/itens", response_model=List[SaidaItemOut])
def get_itens_venda(
    id_venda: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    return db.query(SaidaItem).filter(SaidaItem.id_saida == id_venda).all()


@router.get("/pagamentos/tipos", response_model=List[TipoPagamentoOut])
def list_tipos_pagamento(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    return db.query(TipoPagamento).all()

