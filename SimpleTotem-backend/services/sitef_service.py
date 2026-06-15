"""
Serviço SiTef — subprocesso isolado com suporte a PIX (eventos em tempo real).
"""

import json
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

from core import config as app_config
from services.pinpad_service import comando_worker_sitef
from services.sitef_session import store

logger = logging.getLogger(__name__)

_WORKER_PATH = Path(__file__).resolve().parent / "sitef_worker.py"

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


def _executar_worker(payload: dict, transacao_id: Optional[str] = None) -> dict:
    worker_cmd = comando_worker_sitef()
    body = json.dumps(payload)

    logger.info("[SiTef] Worker: %s modo=%s", " ".join(worker_cmd), payload.get("modo", "transacao"))

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
            if line.startswith("[sitef_worker]"):
                logger.debug(line)
            else:
                _parse_stderr_event(line, transacao_id)
                if transacao_id and line.startswith("{"):
                    logger.info("[SiTef][%s] %s", transacao_id[:8], line)

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


def executar_transacao(
    funcao: int,
    valor_centavos: int,
    cupom: str,
    cnpj_estabelecimento: str = "",
    transacao_id: Optional[str] = None,
) -> dict:
    valor_reais = f"{valor_centavos / 100:.2f}".replace(".", ",")
    payload = {
        "modo": "transacao",
        "funcao": funcao,
        "valor_reais": valor_reais,
        "cupom": cupom,
        "cnpj_estabelecimento": cnpj_estabelecimento,
    }
    return _executar_worker(payload, transacao_id=transacao_id)


_sitef_lock = threading.Lock()


def iniciar_transacao_async(
    funcao: int,
    valor_centavos: int,
    cupom: str,
    cnpj_estabelecimento: str = "",
    total_cobrado: float = 0.0,
) -> str:
    if store.transacao_em_andamento():
        raise RuntimeError("Já existe uma transação SiTef em andamento. Aguarde a conclusão.")

    session = store.criar()
    tid = session.transacao_id

    def _run() -> None:
        with _sitef_lock:
            try:
                resultado = executar_transacao(
                    funcao=funcao,
                    valor_centavos=valor_centavos,
                    cupom=cupom,
                    cnpj_estabelecimento=cnpj_estabelecimento,
                    transacao_id=tid,
                )
                resultado["total_cobrado"] = total_cobrado
                store.finalizar(tid, resultado=resultado)
            except Exception as exc:
                logger.exception("[SiTef] Erro na transação %s", tid)
                store.finalizar(tid, erro=str(exc))

    threading.Thread(target=_run, daemon=True).start()
    return tid


def obter_status_transacao(transacao_id: str) -> Optional[dict]:
    session = store.obter(transacao_id)
    return session.to_dict() if session else None


def resolver_pendencias(cnpj_estabelecimento: str = "") -> None:
    try:
        _executar_worker({
            "modo": "pendencias",
            "cnpj_estabelecimento": cnpj_estabelecimento,
        })
    except Exception as exc:
        logger.warning("[SiTef] Pendências: %s", exc)
