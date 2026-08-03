"""
Serviço SiTef — subprocesso isolado com suporte a PIX (eventos em tempo real).
"""

import json
import logging
import os
import subprocess
import threading
from datetime import datetime
from typing import Optional

from core import config as app_config
from services import vendas_store
from services.pinpad_service import comando_worker_sitef
from services.sitef_session import store

logger = logging.getLogger(__name__)

SITEF_IP = app_config.SITEF_IP
SITEF_ID_LOJA = app_config.SITEF_ID_LOJA
SITEF_ID_TERMINAL = app_config.SITEF_ID_TERMINAL
SITEF_OPERADOR = app_config.SITEF_OPERADOR


def _env_base() -> dict:
    return {
        **os.environ,
        "SITEF_IP": SITEF_IP,
        "SITEF_ID_LOJA": SITEF_ID_LOJA,
        "SITEF_ID_TERMINAL": SITEF_ID_TERMINAL,
        "SITEF_OPERADOR": SITEF_OPERADOR,
        "SITEF_CNPJ_AUTOMACAO": app_config.SITEF_CNPJ_AUTOMACAO,
    }


def _parse_stderr_event(line: str, transacao_id: Optional[str]) -> None:
    line = line.strip()
    if not line.startswith("{"):
        return
    try:
        evento = json.loads(line)
    except json.JSONDecodeError:
        return
    if transacao_id and "evento" in evento:
        store.atualizar_evento(transacao_id, evento)


# Chaves que nunca podem aparecer em log/print, mesmo em diagnóstico — a
# senha do supervisor digitada ao vivo (TC 500) trafega no payload real
# enviado ao worker, mas é redigida antes de qualquer log.
_CAMPOS_SENSIVEIS = {"senha_supervisor"}


def _payload_para_log(payload: dict) -> str:
    redigido = {k: ("***" if k in _CAMPOS_SENSIVEIS else v) for k, v in payload.items()}
    return json.dumps(redigido)


def _executar_worker(payload: dict, transacao_id: Optional[str] = None) -> dict:
    worker_cmd = comando_worker_sitef()
    body = json.dumps(payload)

    # LOG DIAGNÓSTICO — payload enviado ao worker via stdin (campos sensíveis redigidos)
    logger.warning("[SiTef] Worker stdin payload: %s", _payload_para_log(payload))

    proc = subprocess.Popen(
        worker_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_env_base(),
    )
    proc.stdin.write(body)
    proc.stdin.close()

    def _drain_stderr() -> None:
        assert proc.stderr is not None
        for line in proc.stderr:
            line = line.rstrip("\n")
            if not line:
                continue
            if line.startswith("{"):
                _parse_stderr_event(line, transacao_id)
                if transacao_id:
                    logger.info("[SiTef][%s] %s", transacao_id[:8], line)
            else:
                # Captura TODOS os prints do worker/core (debug, diagnóstico, etc.)
                logger.warning("[SiTef worker] %s", line)

    stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
    stderr_thread.start()

    stdout_lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        stdout_lines.append(line.rstrip("\n"))

    proc.wait()
    stderr_thread.join(timeout=5)
    stdout = "\n".join(stdout_lines).strip()
    resultado = None
    if stdout:
        try:
            resultado = json.loads(stdout.splitlines()[-1])
        except json.JSONDecodeError:
            resultado = None

    if resultado is not None and resultado.get("pendencias_resolvidas"):
        return resultado

    if resultado is not None and "aprovada" in resultado:
        return resultado

    if proc.returncode != 0:
        msg = (resultado or {}).get("erro") if resultado else None
        if not msg:
            msg = stdout or "sitef_worker encerrou sem resultado"
        raise RuntimeError(f"SiTef: {msg}")

    raise RuntimeError(f"SiTef: resposta inesperada: {stdout!r}")


def _formatar_valor_sitef(valor_centavos: int) -> str:
    """Formata centavos para exibição humana (ex.: 3490 → '34,90'). NÃO passar para a lib."""
    return f"{valor_centavos // 100},{valor_centavos % 100:02d}"


def executar_transacao(
    funcao: int,
    valor_centavos: int,
    cupom: str,
    cnpj_estabelecimento: str = "",
    transacao_id: Optional[str] = None,
    restricao: str = "",
    num_parcelas: int = 1,
) -> dict:
    valor_display = _formatar_valor_sitef(valor_centavos)
    logger.warning(
        "[SiTef] >>> VALOR PARA PINPAD  funcao=%d  valor_centavos=%d  (display R$%s)  cupom=%s  restricao=%r  parcelas=%d",
        funcao, valor_centavos, valor_display, cupom, restricao, num_parcelas,
    )
    payload = {
        "modo": "transacao",
        "funcao": funcao,
        "valor_centavos": valor_centavos,
        "cupom": cupom,
        "cnpj_estabelecimento": cnpj_estabelecimento,
        "restricao": restricao,
        "num_parcelas": num_parcelas,
    }
    return _executar_worker(payload, transacao_id=transacao_id)


_sitef_lock = threading.Lock()


def iniciar_transacao_async(
    funcao: int,
    valor_centavos: int,
    cupom: str,
    cnpj_estabelecimento: str = "",
    total_cobrado: float = 0.0,
    contexto_venda: Optional[dict] = None,
    restricao: str = "",
    num_parcelas: int = 1,
) -> str:
    if store.transacao_em_andamento():
        raise RuntimeError("Já existe uma transação SiTef em andamento. Aguarde a conclusão.")

    session = store.criar()
    tid = session.transacao_id
    if contexto_venda:
        store.anexar_contexto_venda(tid, contexto_venda)

    def _run() -> None:
        with _sitef_lock:
            try:
                resultado = executar_transacao(
                    funcao=funcao,
                    valor_centavos=valor_centavos,
                    cupom=cupom,
                    cnpj_estabelecimento=cnpj_estabelecimento,
                    transacao_id=tid,
                    restricao=restricao,
                    num_parcelas=num_parcelas,
                )
                resultado["total_cobrado"] = total_cobrado
                store.finalizar(tid, resultado=resultado)
                vendas_store.registrar_venda(tid, {
                    "data_hora": datetime.now().isoformat(),
                    "status": "aprovada" if resultado.get("aprovada") else "negada",
                    "cnpj_estabelecimento": cnpj_estabelecimento,
                    "cupom": cupom,
                    "contexto_venda": contexto_venda,
                    "pagamento_sitef": {
                        "nsu_sitef": resultado.get("nsu_sitef", ""),
                        "nsu_host": resultado.get("nsu_host", ""),
                        "autorizacao": resultado.get("autorizacao", ""),
                        "modalidade": resultado.get("modalidade", ""),
                        "bandeira": resultado.get("bandeira", ""),
                        "linhas_cupom": resultado.get("linhas_cupom", []),
                        "cupom_bruto": resultado.get("cupom_bruto", ""),
                        "total_cobrado": resultado.get("total_cobrado"),
                        "pix": resultado.get("pix", False),
                        "resultado_codigo": resultado.get("resultado"),
                    },
                })
                if resultado.get("aprovada"):
                    _timeout_confirmacao(tid)
            except Exception as exc:
                logger.exception("[SiTef] Erro na transação %s", tid)
                store.finalizar(tid, erro=str(exc))
                vendas_store.registrar_venda(tid, {
                    "data_hora": datetime.now().isoformat(),
                    "status": "erro",
                    "cnpj_estabelecimento": cnpj_estabelecimento,
                    "cupom": cupom,
                    "contexto_venda": contexto_venda,
                    "erro": str(exc),
                })

    threading.Thread(target=_run, daemon=True).start()
    return tid


def obter_status_transacao(transacao_id: str) -> Optional[dict]:
    session = store.obter(transacao_id)
    if not session:
        return None
    return session.to_dict()


def cancelar_transacao_sitef(
    valor_centavos: int,
    cupom_original: str,
    data_original: str,
    nsu_host: str,
    cnpj_estabelecimento: str = "",
    senha_supervisor: Optional[str] = None,
) -> dict:
    """Cancelamento real na Fiserv (função SiTef 200 — Menu de Cancelamento), usado pelo estorno do
    painel de cancelamento. Serializado com o mesmo lock/checagem das
    transações normais — não pode rodar em paralelo com uma venda no pinpad.

    senha_supervisor: digitada ao vivo no painel admin para autorizar o TC 500
    (requisito Fiserv) — nunca é logada, só trafega no payload real do worker."""
    if store.transacao_em_andamento():
        raise RuntimeError("Já existe uma transação SiTef em andamento. Aguarde a conclusão.")
    with _sitef_lock:
        return _executar_worker({
            "modo": "cancelamento",
            "valor_centavos": valor_centavos,
            "cupom_original": cupom_original,
            "data_original": data_original,
            "nsu_host": nsu_host,
            "cnpj_estabelecimento": cnpj_estabelecimento,
            "senha_supervisor": senha_supervisor,
        })


def confirmar_pagamento_sitef(confirma: int) -> dict:
    """
    Chama FinalizaFuncaoSiTefInterativoA via worker.
    Deve ser chamado APÓS impressão do cupom TEF e emissão do XML fiscal (Item 8.1.1).
    confirma=1 → confirma pagamento
    confirma=0 → desfaz pagamento
    """
    return _executar_worker({"modo": "confirmar", "confirma": confirma})


def _timeout_confirmacao(transacao_id: str, delay: int = 30) -> None:
    """Fallback: se /vendas/confirmar não chegar em 'delay' segundos, confirma automaticamente."""
    def _check() -> None:
        import time
        time.sleep(delay)
        session = store.obter(transacao_id)
        if session and session.status == "aprovada" and not session.confirmada:
            logger.warning(
                "[SiTef] Timeout confirmação — confirmando automaticamente transacao=%s", transacao_id
            )
            try:
                confirmar_pagamento_sitef(1)
                store.marcar_confirmada(transacao_id)
            except Exception as exc:
                logger.error("[SiTef] Falha no timeout de confirmação: %s", exc)
    threading.Thread(target=_check, daemon=True).start()


def resolver_pendencias(cnpj_estabelecimento: str = "") -> None:
    try:
        _executar_worker({
            "modo": "pendencias",
            "cnpj_estabelecimento": cnpj_estabelecimento,
        })
    except Exception as exc:
        logger.warning("[SiTef] Pendências: %s", exc)
