import logging
import unicodedata
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.orm import Empresa
from models.schemas import (
    IniciaVendaRequest, IniciaVendaResponse, ItemVendaCalculado,
    IniciaTransacaoRequest, IniciaTransacaoStartResponse, TransacaoStatusResponse,
    ConfirmarPagamentoRequest, EstornarPedidoRequest,
)
from services import sitef_service, vendas_store
from services.sitef_session import store
from services.terminal_service import resolver_terminal_atual

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vendas", tags=["vendas"])

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
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """
    Inicia transação SiTef (cartão ou PIX) em background.
    O frontend deve consultar GET /vendas/transacao/{id} para QR Code e status.
    """
    # LOG DIAGNÓSTICO — visível mesmo sem debug habilitado
    logger.warning(
        "[Transacao] >>> PAYLOAD RAW total_cliente=%r  itens=%r",
        req.total_cliente,
        [(i.produto_id, float(i.quantidade), float(i.preco_unitario)) for i in req.itens],
    )

    # 1. Re-calcular total
    total_recalculado = round(
        sum(float(i.quantidade) * float(i.preco_unitario) for i in req.itens), 2
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
    # Tenta mapeamento direto pelo ID numérico (SimplesFique: 3=crédito, 4=débito, 17/20=PIX)
    # Confirmado no pinpad real: função SiTef 3=crédito, 2=débito (invertido do que a
    # documentação da CliSiTef sugere à primeira vista — vale reconferir se a Fiserv
    # atualizar a doc).
    _SFIQUE_ID_MAP = {"3": 3, "4": 2, "17": 122, "20": 122}
    mid = req.metodo_pagamento_id.strip().lstrip("0") or "0"
    if mid in _SFIQUE_ID_MAP:
        funcao_sitef = _SFIQUE_ID_MAP[mid]
        descricao_pag = mid
    else:
        descricao_pag = mid
        funcao_sitef = _metodo_para_funcao(descricao_pag)
    logger.info(
        "[Transacao] valor_centavos=%d total_final=%.2f valor_sitef=%s funcao_sitef=%d desc=%s cupom=%s",
        valor_centavos,
        total_final,
        _formatar_valor_sitef(valor_centavos),
        funcao_sitef,
        descricao_pag,
        cupom,
    )

    id_terminal = req.id_terminal
    if not id_terminal:
        terminal = resolver_terminal_atual(db, request.client.host if request.client else None)
        id_terminal = terminal["id"] if terminal else None

    restricao = ""
    num_parcelas = req.num_parcelas
    if funcao_sitef == 3:  # crédito
        restricao = _montar_restricao_parcelamento(req.tipo_parcelamento, num_parcelas)

    contexto_venda = {
        "itens": [i.model_dump() for i in req.itens],
        "total": total_final,
        "metodo_pagamento_id": req.metodo_pagamento_id,
        "id_terminal": id_terminal,
    }

    try:
        transacao_id = sitef_service.iniciar_transacao_async(
            funcao=funcao_sitef,
            valor_centavos=valor_centavos,
            cupom=cupom,
            cnpj_estabelecimento=cnpj_estabelecimento,
            total_cobrado=total_final,
            contexto_venda=contexto_venda,
            restricao=restricao,
            num_parcelas=num_parcelas,
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


def _montar_restricao_parcelamento(tipo: str, num_parcelas: int) -> str:
    """Monta restrição para IniciaFuncaoSiTefInterativo conforme tipo de crédito."""
    if num_parcelas == 1 or tipo == "a_vista":
        return "{TransacoesHabilitadas=26}"
    elif tipo == "parcelado_estabelecimento":
        return "{TransacoesHabilitadas=27}"
    elif tipo == "parcelado_administradora":
        return "{TransacoesHabilitadas=39}"
    return ""


def _normalize_ascii_lower(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    return texto.encode("ascii", "ignore").decode().lower()


def _formatar_valor_sitef(valor_centavos: int) -> str:
    """Formata centavos para o padrão CliSiTef: '34,90'."""
    return f"{valor_centavos // 100},{valor_centavos % 100:02d}"


def _metodo_para_funcao(descricao: str) -> int:
    """
    Mapeia o ID ou descrição do tipo de pagamento para o código de função SiTef.
    IDs numéricos do SimplesFique têm prioridade: 3=crédito, 4=débito, 17/20=PIX.
    Fallback por descrição para compatibilidade com banco local.
    """
    # Mapeamento direto por ID numérico (SimplesFique)
    # Função SiTef 3=crédito, 2=débito — confirmado no pinpad real.
    _ID_MAP = {"3": 3, "4": 2, "17": 122, "20": 122}
    if str(descricao).strip() in _ID_MAP:
        return _ID_MAP[str(descricao).strip()]

    m = _normalize_ascii_lower(descricao)
    if "cred" in m:
        return 3  # Crédito
    if "deb" in m:
        return 2  # Débito
    if "voucher" in m or "beneficio" in m or "bene" in m:
        return 4
    if "pix" in m or "carteira" in m or "digital" in m or "qr" in m or "instantaneo" in m:
        return 122  # Carteira Digital — Venda (PIX)
    return 0  # Menu geral


# ─── Confirmação pós-impressão (Item 8.1.1 CliSiTef AA) ──────────────────────

@router.post("/confirmar")
def confirmar_pagamento(
    body: ConfirmarPagamentoRequest,
    _: str = Depends(get_current_user),
):
    """
    Confirma ou desfaz a transação SiTef após impressão do cupom TEF e XML fiscal.
    Regra: confirma=1 apenas se impressao_ok=True E xml_emitido=True.
    """
    deve_confirmar = body.impressao_ok and body.xml_emitido
    confirma = 1 if deve_confirmar else 0

    try:
        sitef_service.confirmar_pagamento_sitef(confirma)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    store.marcar_confirmada(body.transacao_id)
    vendas_store.registrar_venda(body.transacao_id, {
        "confirmado": bool(confirma),
        "impressao_ok": body.impressao_ok,
        "xml_emitido": body.xml_emitido,
        "codigo_senha": body.codigo_senha,
        "cupom_fiscal": body.cupom_fiscal,
    })

    return {"confirmado": bool(confirma), "confirma": confirma}


# ─── Base de vendas para evidência de homologação (NSU, cupom, etc.) ─────────

@router.get("/homologacao")
def listar_vendas_homologacao(_: str = Depends(get_current_user)):
    """Todas as vendas registradas (aprovadas, negadas e com erro), com dados
    completos de pagamento SiTef/Fiserv — usado como base local para a
    homologação (sem depender de nenhum backend externo)."""
    return {"vendas": vendas_store.listar_vendas()}


# ─── Painel de cancelamento — base local (JSON) enquanto não há SimplesFique ──

@router.get("/pedidos")
def listar_pedidos_aprovados(
    terminal_id: Optional[int] = None,
    codigo_senha: Optional[str] = None,
    data_operacao: Optional[str] = None,
    _: str = Depends(get_current_user),
):
    """Pagamentos aprovados no pinpad (dados de vendas_homologacao.json),
    usados pelo painel de cancelamento como base local temporária."""
    pedidos = vendas_store.listar_pedidos_aprovados(
        terminal_id=terminal_id,
        codigo_senha=codigo_senha,
        data_operacao=data_operacao,
    )
    return {"pedidos": pedidos}


@router.patch("/pedidos/{transacao_id}/estornar")
def estornar_pedido(
    transacao_id: str,
    body: EstornarPedidoRequest,
    _: str = Depends(get_current_user),
):
    """Cancela a venda na Fiserv (função SiTef 200 — Menu de Cancelamento, via NSU host da transação
    original) e só marca como estornada na base local se a Fiserv confirmar."""
    if not body.senha_supervisor or not body.senha_supervisor.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha do supervisor é obrigatória para autorizar o cancelamento",
        )

    venda = vendas_store.obter_venda(transacao_id)
    if not venda or venda.get("status") != "aprovada":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido aprovado não encontrado")
    if venda.get("estornado"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pedido já estornado")

    contexto = venda.get("contexto_venda") or {}
    pagamento = venda.get("pagamento_sitef") or {}
    cupom_original = venda.get("cupom") or ""
    if not cupom_original:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Venda sem cupom original registrado — não é possível cancelar na Fiserv",
        )

    valor_centavos = int(round(float(pagamento.get("total_cobrado") or contexto.get("total") or 0) * 100))
    nsu_host = pagamento.get("nsu_host") or pagamento.get("nsu_sitef") or ""

    try:
        resultado = sitef_service.cancelar_transacao_sitef(
            valor_centavos=valor_centavos,
            cupom_original=cupom_original,
            data_original=cupom_original[:8],
            nsu_host=nsu_host,
            cnpj_estabelecimento=venda.get("cnpj_estabelecimento") or "",
            senha_supervisor=body.senha_supervisor,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"CliSiTef não disponível: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Falha ao cancelar na Fiserv: {exc}")

    if not resultado.get("aprovada"):
        detail = resultado.get("erro") or f"Cancelamento recusado pela Fiserv (código {resultado.get('resultado')})"
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)

    pedido = vendas_store.marcar_estornada(transacao_id, body.motivo, resultado_cancelamento=resultado)
    if not pedido:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pedido já estornado")
    return {"pedido": pedido}

