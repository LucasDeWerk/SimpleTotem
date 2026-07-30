"""Persistência local de vendas aprovadas (tven_saida + itens + pagamento)."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def gravar_venda_aprovada(
    db: Session,
    *,
    itens: List[Dict[str, Any]],
    total: float,
    metodo_pagamento_id: str,
    resultado_sitef: Dict[str, Any],
    id_terminal: Optional[int] = None,
) -> int:
    """Grava venda, itens e pagamento. Retorna id_saida."""
    if not itens:
        raise ValueError("Venda sem itens")

    dtemissao = _now_str()
    vlr_venda = round(float(total), 2)
    id_terminal_val = int(id_terminal) if id_terminal else None

    params_saida = {
        "dtemissao": dtemissao,
        "vlr_venda": vlr_venda,
        "id_terminal": id_terminal_val,
    }

    if id_terminal_val is not None:
        cur = db.execute(
            text("""
                INSERT INTO tven_saida (
                    dtemissao, id_cfop, id_clifor, id_vendedor, situacao,
                    vlr_venda, custo_total_venda,
                    base_icms, vlr_icms, base_icms_subst, vlr_icms_subst,
                    base_pis_produto, vlr_pis_produto, base_cofins_produto, vlr_cofins_produto,
                    id_terminal
                ) VALUES (
                    :dtemissao, '5102', 0, 0, 'F',
                    :vlr_venda, 0,
                    0, 0, 0, 0, 0, 0, 0, 0,
                    :id_terminal
                )
            """),
            params_saida,
        )
    else:
        cur = db.execute(
            text("""
                INSERT INTO tven_saida (
                    dtemissao, id_cfop, id_clifor, id_vendedor, situacao,
                    vlr_venda, custo_total_venda,
                    base_icms, vlr_icms, base_icms_subst, vlr_icms_subst,
                    base_pis_produto, vlr_pis_produto, base_cofins_produto, vlr_cofins_produto
                ) VALUES (
                    :dtemissao, '5102', 0, 0, 'F',
                    :vlr_venda, 0,
                    0, 0, 0, 0, 0, 0, 0, 0
                )
            """),
            params_saida,
        )

    id_saida = int(cur.lastrowid)

    for item in itens:
        produto_id = int(item["produto_id"])
        qtd = float(item["quantidade"])
        preco = float(item["preco_unitario"])
        total_item = round(qtd * preco, 4)
        db.execute(
            text("""
                INSERT INTO tven_saidaitens (
                    id_saida, id_produto,
                    custo_aquisicao, custo_medio, custo_compra,
                    vlr_unitario_sugerido, vlr_unitario_praticado,
                    quantidade, vlr_total_item,
                    base_icms_item, vlr_icms_item,
                    base_pis_item, vlr_pis_item,
                    base_cofins_item, vlr_cofins_item
                ) VALUES (
                    :id_saida, :id_produto,
                    0, 0, 0,
                    :preco, :preco,
                    :qtd, :total_item,
                    0, 0, 0, 0, 0, 0
                )
            """),
            {
                "id_saida": id_saida,
                "id_produto": produto_id,
                "preco": preco,
                "qtd": qtd,
                "total_item": total_item,
            },
        )

    tipo_pag = str(metodo_pagamento_id)[:2] if metodo_pagamento_id else None
    db.execute(
        text("""
            INSERT INTO tven_saidapagamento (
                id_saida, id_tipo_pagamento, vlr_pagamento,
                nsu_sitef, nsu_host, autorizacao, bandeira, modalidade,
                pix, cupom_bruto, dh_pagamento
            ) VALUES (
                :id_saida, :id_tipo_pagamento, :vlr_pagamento,
                :nsu_sitef, :nsu_host, :autorizacao, :bandeira, :modalidade,
                :pix, :cupom_bruto, :dh_pagamento
            )
        """),
        {
            "id_saida": id_saida,
            "id_tipo_pagamento": tipo_pag,
            "vlr_pagamento": vlr_venda,
            "nsu_sitef": (resultado_sitef.get("nsu_sitef") or "")[:20],
            "nsu_host": (resultado_sitef.get("nsu_host") or "")[:20],
            "autorizacao": (resultado_sitef.get("autorizacao") or "")[:20],
            "bandeira": (resultado_sitef.get("bandeira") or "")[:30],
            "modalidade": (resultado_sitef.get("modalidade") or "")[:30],
            "pix": 1 if resultado_sitef.get("pix") else 0,
            "cupom_bruto": resultado_sitef.get("cupom_bruto") or "",
            "dh_pagamento": dtemissao,
        },
    )

    db.commit()
    logger.info(
        "Venda gravada localmente | id_saida=%s terminal=%s total=%.2f",
        id_saida,
        id_terminal_val,
        vlr_venda,
    )
    return id_saida
