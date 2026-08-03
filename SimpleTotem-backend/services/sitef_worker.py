#!/usr/bin/env python3
"""
sitef_worker.py — subprocesso isolado para CliSiTef (cartão + PIX).
stdin  → JSON
stdout → JSON resultado
stderr → logs + eventos JSON (PIX/QR/mensagens)
"""

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
                    format="[sitef_worker] %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from services.sitef_core import (  # noqa: E402
    executar_transacao,
    cancelar_transacao,
    confirmar_transacao,
    gerar_cupom_fiscal,
    resolver_pendencias,
)


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
        modo = payload.get("modo", "transacao")
        cnpj = str(payload.get("cnpj_estabelecimento", ""))

        if modo == "confirmar":
            confirma = int(payload.get("confirma", 0))
            confirmar_transacao(confirma)
            sys.stdout.write(json.dumps({"confirmado": True, "confirma": confirma}) + "\n")
            sys.stdout.flush()
            return 0

        if modo == "pendencias":
            resolver_pendencias(cnpj_estabelecimento=cnpj)
            sys.stdout.write(json.dumps({"pendencias_resolvidas": True}) + "\n")
            sys.stdout.flush()
            return 0

        if modo == "cancelamento":
            # senha_supervisor: digitada ao vivo no painel admin (TC 500) — nunca logar.
            resultado = cancelar_transacao(
                valor_centavos=int(payload["valor_centavos"]),
                cupom_original=str(payload["cupom_original"]),
                data_original=str(payload["data_original"]),
                nsu_host=str(payload.get("nsu_host") or ""),
                cnpj_estabelecimento=cnpj,
                senha_supervisor=payload.get("senha_supervisor") or None,
            )
            sys.stdout.write(json.dumps(resultado) + "\n")
            sys.stdout.flush()
            return 0

        funcao = int(payload["funcao"])
        valor_centavos = int(payload["valor_centavos"])
        cupom = str(payload.get("cupom") or gerar_cupom_fiscal())
        restricao = str(payload.get("restricao") or "")
        num_parcelas = int(payload.get("num_parcelas") or 1)

        executar_transacao(
            funcao=funcao,
            valor_centavos=valor_centavos,
            cupom=cupom,
            cnpj_estabelecimento=cnpj,
            restricao=restricao,
            num_parcelas=num_parcelas,
        )
        return 0
    except Exception as exc:
        logger.error("Erro fatal: %s", exc, exc_info=True)
        sys.stdout.write(json.dumps({"erro": str(exc), "aprovada": False}) + "\n")
        sys.stdout.flush()
        return 1


if __name__ == "__main__":
    sys.exit(main())
