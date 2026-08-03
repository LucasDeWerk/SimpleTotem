"""Registro de todas as vendas em JSON — base de evidência para a homologação
Fiserv (NSU, autorização, cupom TEF, cupom fiscal, etc.).

Cada transação SiTef gera (ou atualiza) uma entrada identificada por
`transacao_id`, tanto para vendas aprovadas quanto negadas/com erro.
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from core.config import DATA_DIR

VENDAS_FILE: Path = DATA_DIR / "vendas_homologacao.json"
_lock = threading.Lock()

_FORMAS_PAGAMENTO = {
    "3": "Cartão de Crédito",
    "4": "Cartão de Débito",
    "17": "PIX",
    "20": "PIX",
}


def _ler() -> list:
    if not VENDAS_FILE.exists():
        return []
    try:
        return json.loads(VENDAS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _escrever(vendas: list) -> None:
    VENDAS_FILE.write_text(json.dumps(vendas, ensure_ascii=False, indent=2), encoding="utf-8")


def registrar_venda(transacao_id: str, dados: Dict[str, Any]) -> None:
    """Cria o registro da venda pelo transacao_id, ou atualiza se já existir
    (usado para acrescentar confirmação/cupom fiscal depois da aprovação)."""
    with _lock:
        vendas = _ler()
        for venda in vendas:
            if venda.get("transacao_id") == transacao_id:
                venda.update(dados)
                _escrever(vendas)
                return
        vendas.append({"transacao_id": transacao_id, **dados})
        _escrever(vendas)


def listar_vendas() -> list:
    with _lock:
        return _ler()


def obter_venda(transacao_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        for venda in _ler():
            if venda.get("transacao_id") == transacao_id:
                return venda
        return None


def _mapear_pedido(venda: Dict[str, Any]) -> Dict[str, Any]:
    """Converte um registro bruto de venda no formato usado pelo painel de
    cancelamento (herdado do antigo formato de 'pedidos' do SimplesFique)."""
    contexto = venda.get("contexto_venda") or {}
    pagamento = venda.get("pagamento_sitef") or {}
    itens = contexto.get("itens") or []
    metodo_id = str(contexto.get("metodo_pagamento_id") or "").strip()

    return {
        "id": venda.get("transacao_id"),
        "codigo_senha": venda.get("codigo_senha"),
        "origem": "totem",
        "terminal_id": contexto.get("id_terminal"),
        "status_pagamento": "estornado" if venda.get("estornado") else "aprovado",
        "data_operacao": (venda.get("data_hora") or "")[:10],
        "documento": None,  # sem integração NF-e neste app
        "total": contexto.get("total", pagamento.get("total_cobrado")),
        "status": "estornado" if venda.get("estornado") else "concluido",
        "motivo_estorno": venda.get("motivo_estorno"),
        "pagamento": {
            "forma_pagamento": _FORMAS_PAGAMENTO.get(metodo_id, pagamento.get("modalidade") or metodo_id),
            "bandeira": pagamento.get("bandeira"),
            "valor": pagamento.get("total_cobrado", contexto.get("total")),
            "nsu": pagamento.get("nsu_sitef") or pagamento.get("nsu_host"),
            "codigo_autorizacao": pagamento.get("autorizacao"),
            "pago_em": venda.get("data_hora"),
        },
        "itens": [
            {
                "quantidade": item.get("quantidade"),
                "nome_produto": item.get("descricao"),
                "valor_total": round(float(item.get("quantidade") or 0) * float(item.get("preco_unitario") or 0), 2),
            }
            for item in itens
        ],
    }


def listar_pedidos_aprovados(
    *,
    terminal_id: Optional[int] = None,
    codigo_senha: Optional[str] = None,
    data_operacao: Optional[str] = None,
) -> list:
    """Vendas aprovadas no pinpad, no formato usado pelo painel de cancelamento."""
    with _lock:
        vendas = [v for v in _ler() if v.get("status") == "aprovada"]

    pedidos = [_mapear_pedido(v) for v in vendas]

    if terminal_id is not None:
        pedidos = [p for p in pedidos if p.get("terminal_id") == terminal_id]
    if codigo_senha:
        pedidos = [p for p in pedidos if str(p.get("codigo_senha") or "") == str(codigo_senha)]
    if data_operacao:
        pedidos = [p for p in pedidos if p.get("data_operacao") == data_operacao]

    return pedidos


def marcar_estornada(
    transacao_id: str,
    motivo: str,
    *,
    resultado_cancelamento: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Marca a venda como estornada — chamado só depois que o cancelamento na
    Fiserv (função SiTef 123) já foi confirmado. Retorna o pedido no formato
    do painel, ou None se não encontrada/já estornada/não aprovada."""
    with _lock:
        vendas = _ler()
        alvo = None
        for venda in vendas:
            if venda.get("transacao_id") == transacao_id:
                alvo = venda
                break
        if not alvo or alvo.get("status") != "aprovada" or alvo.get("estornado"):
            return None
        alvo["estornado"] = True
        alvo["motivo_estorno"] = motivo
        alvo["data_estorno"] = datetime.now().isoformat()
        if resultado_cancelamento is not None:
            alvo["cancelamento_sitef"] = resultado_cancelamento
        _escrever(vendas)
        return _mapear_pedido(alvo)
