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
    executar_funcao_administrativa,
    _ler_mensagem_stdin,
)

# Se a confirmação (Item 8.1.1 — pós impressão/XML fiscal) não chegar nesse
# tempo, confirma por padrão: a transação já foi aprovada pela CliSiTef,
# então não responder é mais seguro que desfazer um pagamento já aceito.
TIMEOUT_CONFIRMACAO_SEGUNDOS = 180.0


def main() -> int:
    try:
        # readline() (não read()): para "funcao_admin" o backend mantém o
        # stdin aberto e envia novas linhas JSON com a resposta do operador
        # enquanto este processo ainda está rodando (protocolo interativo).
        linha_inicial = sys.stdin.readline()
        payload = json.loads(linha_inicial)
        modo = payload.get("modo", "transacao")
        cnpj = str(payload.get("cnpj_estabelecimento", ""))

        if modo == "funcao_admin":
            funcao_codigo = str(payload["funcao_codigo"])
            resultado = executar_funcao_administrativa(
                funcao_codigo=funcao_codigo,
                cnpj_estabelecimento=cnpj,
            )
            sys.stdout.write(json.dumps(resultado, ensure_ascii=False) + "\n")
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

        resultado = executar_transacao(
            funcao=funcao,
            valor_centavos=valor_centavos,
            cupom=cupom,
            cnpj_estabelecimento=cnpj,
            restricao=restricao,
            num_parcelas=num_parcelas,
        )

        if resultado.get("pendente_confirmacao"):
            # Aprovada — fica de pé NESTE MESMO processo esperando o backend
            # mandar confirmar/desfazer (Item 8.1.1), depois da impressão do
            # cupom TEF e emissão do XML fiscal.
            resposta = _ler_mensagem_stdin(timeout=TIMEOUT_CONFIRMACAO_SEGUNDOS)
            if resposta and resposta.get("acao") == "confirmar":
                confirma = int(resposta.get("confirma", 1))
            else:
                logger.warning(
                    "Timeout/sem confirmação em %.0fs — confirmando por padrão (transação já aprovada).",
                    TIMEOUT_CONFIRMACAO_SEGUNDOS,
                )
                confirma = 1
            # cupom/data/hora identificam a transação no Finaliza — precisam ser
            # os mesmos do Inicia dela.
            confirmar_transacao(
                confirma,
                cupom=resultado.get("cupom", cupom),
                data=resultado.get("data_fiscal", ""),
                hora=resultado.get("hora_fiscal", ""),
                cnpj_estabelecimento=cnpj,
            )

        return 0
    except Exception as exc:
        logger.error("Erro fatal: %s", exc, exc_info=True)
        # str(exc) pode vir vazio (ex.: exceção levantada sem argumentos) —
        # sem fallback, a tela final perderia a mensagem real da CliSiTef.
        erro_msg = str(exc) or f"{type(exc).__name__} (sem mensagem)"
        sys.stdout.write(json.dumps({"erro": erro_msg, "aprovada": False}) + "\n")
        sys.stdout.flush()
        return 1


if __name__ == "__main__":
    sys.exit(main())
