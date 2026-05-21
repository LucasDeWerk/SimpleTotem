"""
Serviço SiTef — invoca sitef_worker.py como subprocesso isolado.

A libclisitef.so causa segfault quando chamada de threads de worker do uvicorn.
Rodando em subprocesso separado:
  - A lib executa na thread principal do subprocesso
  - Um crash na lib mata apenas o subprocesso, não o servidor
  - O resultado é comunicado via JSON em stdout
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_WORKER_PATH = Path(__file__).resolve().parent / "sitef_worker.py"

SITEF_IP          = os.getenv("SITEF_IP",          "192.168.10.50")
SITEF_ID_LOJA     = os.getenv("SITEF_ID_LOJA",     "00000000")
SITEF_ID_TERMINAL = os.getenv("SITEF_ID_TERMINAL", "ST000001")
SITEF_OPERADOR    = os.getenv("SITEF_OPERADOR",    "01")


def executar_transacao(funcao: int, valor_centavos: int, cupom: str) -> dict:
    """
    Executa uma transação SiTef completa via subprocesso isolado (bloqueante).

    Parâmetros:
        funcao          : código SiTef (0=menu, 2=crédito, 3=débito, 4=voucher)
        valor_centavos  : valor total em centavos (inteiro)
        cupom           : número do cupom fiscal (string)

    Retorna dict com campos:
        aprovada, resultado, nsu_sitef, nsu_host, autorizacao,
        modalidade, bandeira, dados, linhas_cupom
    """
    # Converter para formato brasileiro "10,00" (o que a lib espera)
    valor_reais = f"{valor_centavos / 100:.2f}".replace(".", ",")

    logger.info("[SiTef] valor_centavos=%d → valor_reais=%s", valor_centavos, valor_reais)

    payload = json.dumps({
        "funcao":      funcao,
        "valor_reais": valor_reais,
        "cupom":       cupom,
    })

    env = {
        **os.environ,
        "SITEF_IP":          SITEF_IP,
        "SITEF_ID_LOJA":     SITEF_ID_LOJA,
        "SITEF_ID_TERMINAL": SITEF_ID_TERMINAL,
        "SITEF_OPERADOR":    SITEF_OPERADOR,
    }

    logger.info("[SiTef] Iniciando subprocesso: funcao=%d valor=%s cupom=%s",
                funcao, valor_reais, cupom)

    try:
        proc = subprocess.run(
            [sys.executable, str(_WORKER_PATH)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=None,   # sem timeout — a transação pode demorar (digitação de senha, etc.)
            env=env,
        )
    except Exception as exc:
        raise RuntimeError(f"Falha ao iniciar sitef_worker: {exc}") from exc

    # Propaga logs do worker para o logger do serviço
    if proc.stderr:
        for line in proc.stderr.strip().splitlines():
            logger.debug("[sitef_worker] %s", line)

    # Tenta parsear o JSON de saída independente do returncode —
    # o worker emite o resultado ANTES de chamar FinalizaFuncao,
    # então mesmo que a lib crash no Finaliza o JSON já chegou.
    stdout = proc.stdout.strip()
    resultado = None
    if stdout:
        try:
            resultado = json.loads(stdout.splitlines()[-1])  # pega a última linha JSON
        except json.JSONDecodeError:
            resultado = None

    if resultado is not None and "aprovada" in resultado:
        logger.info("[SiTef] Resultado recebido: aprovada=%s resultado=%s",
                    resultado.get("aprovada"), resultado.get("resultado"))
        return resultado

    # Se não veio resultado válido, trata como erro
    if proc.returncode != 0:
        msg = (resultado or {}).get("erro") if resultado else None
        if not msg:
            msg = stdout or "sitef_worker encerrou sem resultado"
        raise RuntimeError(f"SiTef: {msg}")

    raise RuntimeError(f"SiTef: resposta inesperada do worker: {stdout!r}")

