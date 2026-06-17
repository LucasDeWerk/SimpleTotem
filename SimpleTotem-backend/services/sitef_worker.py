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
    gerar_cupom_fiscal,
    resolver_pendencias,
)


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
        modo = payload.get("modo", "transacao")
        cnpj = str(payload.get("cnpj_estabelecimento", ""))

        if modo == "pendencias":
            resolver_pendencias(cnpj_estabelecimento=cnpj)
            sys.stdout.write(json.dumps({"pendencias_resolvidas": True}) + "\n")
            sys.stdout.flush()
            return 0

        funcao = int(payload["funcao"])
        # Centavos como string inteira: "3490" para R$ 34,90 — é o que a lib C espera
        valor_centavos = int(payload["valor_centavos"])
        cupom = str(payload.get("cupom") or gerar_cupom_fiscal())

        executar_transacao(
            funcao=funcao,
            valor_centavos=valor_centavos,
            cupom=cupom,
            cnpj_estabelecimento=cnpj,
        )
        return 0
    except Exception as exc:
        logger.error("Erro fatal: %s", exc, exc_info=True)
        sys.stdout.write(json.dumps({"erro": str(exc), "aprovada": False}) + "\n")
        sys.stdout.flush()
        return 1


if __name__ == "__main__":
    sys.exit(main())
