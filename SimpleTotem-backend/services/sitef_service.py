"""
Serviço SiTef — subprocesso isolado com suporte a PIX (eventos em tempo real).
"""

import json
import logging
import os
import subprocess
import threading
from datetime import datetime
from typing import Dict, Optional

from core import config as app_config
from services import vendas_store
from services.pinpad_service import comando_worker_sitef
from services.sitef_session import store
from services.homologacao_session import store as homolog_store

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


# Transações em andamento cujo worker mantém o stdin aberto — usado só pelo
# modo "transacao", pra permitir responder de verdade a confirmação de
# cancelamento via ANULA (Seq. 9), sem fechar o canal como as demais chamadas
# (cancelamento/confirmar/pendências), que continuam no modelo write-and-close.
_processos_transacao_ativos: Dict[str, subprocess.Popen] = {}
_processos_transacao_lock = threading.Lock()


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
    manter_stdin_aberto = payload.get("modo") == "transacao" and transacao_id is not None
    if manter_stdin_aberto:
        # readline() no worker precisa de um terminador — antes o close()
        # fazia esse papel (EOF); mantendo o stdin aberto, precisa do \n.
        proc.stdin.write(body + "\n")
        proc.stdin.flush()
        with _processos_transacao_lock:
            _processos_transacao_ativos[transacao_id] = proc
    else:
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
    resultado: Optional[dict] = None
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip("\n")
        stdout_lines.append(line)
        if manter_stdin_aberto and resultado is None:
            try:
                candidato = json.loads(line)
            except json.JSONDecodeError:
                candidato = None
            if isinstance(candidato, dict) and "aprovada" in candidato:
                # Transação decidida (aprovada/negada/erro) — não espera o
                # processo terminar. Se aprovada, ele fica de pé esperando a
                # confirmação (ver confirmar_pagamento_sitef); a limpeza final
                # roda em background, sem bloquear quem já tem o resultado.
                resultado = candidato
                threading.Thread(
                    target=_aguardar_saida_worker, args=(proc, stderr_thread, transacao_id), daemon=True,
                ).start()
                return resultado

    proc.wait()
    stderr_thread.join(timeout=5)

    if manter_stdin_aberto:
        with _processos_transacao_lock:
            _processos_transacao_ativos.pop(transacao_id, None)
        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
        except Exception:
            pass

    stdout = "\n".join(stdout_lines).strip()
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


def _aguardar_saida_worker(
    proc: subprocess.Popen, stderr_thread: threading.Thread, transacao_id: Optional[str],
) -> None:
    """Drena o resto do stderr e espera o processo encerrar de vez (depois de
    receber o confirmar/desfazer, ou imediatamente se já não tinha nada
    pendente) — roda em background, sem bloquear quem já recebeu o resultado
    da transação."""
    proc.wait()
    stderr_thread.join(timeout=5)
    if transacao_id:
        with _processos_transacao_lock:
            _processos_transacao_ativos.pop(transacao_id, None)
    try:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
    except Exception:
        pass


def responder_confirmacao_cancelamento(transacao_id: str, confirma: bool) -> None:
    """Envia a resposta real do cliente/operador (Sim/Não na tela do totem)
    pra confirmação de cancelamento via ANULA (Seq. 9) — o worker está
    bloqueado esperando isso em services/sitef_core.py
    (_aguardar_confirmacao_cancelamento)."""
    with _processos_transacao_lock:
        proc = _processos_transacao_ativos.get(transacao_id)
    if not proc or proc.stdin is None or proc.stdin.closed:
        raise RuntimeError("Transação não encontrada ou já finalizada.")
    mensagem = {"acao": "responder_cancelamento", "confirma": confirma}
    proc.stdin.write(json.dumps(mensagem) + "\n")
    proc.stdin.flush()


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
    session.cnpj_estabelecimento = cnpj_estabelecimento
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

                # Falha de comunicação/execução (ex.: IniciaFuncaoSiTef falhou por
                # timeout, código -5 "Sem comunicação com o SiTef") não levanta
                # exceção — o worker devolve {"erro": ..., "aprovada": False} como
                # resultado "normal" (ver sitef_worker.py). Sem este desvio, a
                # mensagem real da CliSiTef se perdia e a tela só mostrava o
                # fallback genérico "Pagamento não aprovado". Distingue de uma
                # recusa legítima do loop (cancelamento -2/-6 etc.), que não tem
                # chave "erro" no resultado — esses continuam pelo caminho normal.
                if resultado.get("erro") and not resultado.get("aprovada"):
                    store.finalizar(tid, erro=resultado["erro"])
                    vendas_store.registrar_venda(tid, {
                        "data_hora": datetime.now().isoformat(),
                        "status": "erro",
                        "cnpj_estabelecimento": cnpj_estabelecimento,
                        "cupom": cupom,
                        "contexto_venda": contexto_venda,
                        "erro": resultado["erro"],
                    })
                    return

                resultado["total_cobrado"] = total_cobrado
                # Diagnóstico: todos os tipoCampo devolvidos (menos os textos de cupom),
                # para conferir de onde sai o código de autorização (ex.: PIX).
                campos_sitef = {
                    k: v for k, v in (resultado.get("dados") or {}).items() if k not in ("121", "122")
                }
                logger.warning(
                    "[SiTef] Campos devolvidos transacao=%s pix=%s aprovada=%s: %s",
                    tid, resultado.get("pix"), resultado.get("aprovada"), campos_sitef,
                )
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
                        "documento_pix": resultado.get("documento_pix", ""),
                        "campos_sitef": campos_sitef,
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


def confirmar_pagamento_sitef(confirma: int, transacao_id: str) -> None:
    """
    Envia a confirmação (Item 8.1.1 — FinalizaFuncaoSiTefInterativoA) pro
    MESMO processo/worker que rodou o IniciaFuncaoSiTefInterativoA e o loop
    daquela transação — precisa ser o mesmo processo/sessão, senão a
    CliSiTef crasha nativamente (confirmado: configurar a lib de novo num
    processo novo não é suficiente, o Finaliza ainda falha sem saída
    nenhuma). O worker fica de pé esperando essa mensagem depois de reportar
    "aprovada" (ver sitef_worker.py).
    confirma=1 → confirma pagamento
    confirma=0 → desfaz pagamento
    """
    with _processos_transacao_lock:
        proc = _processos_transacao_ativos.get(transacao_id)
    if not proc or proc.stdin is None or proc.stdin.closed:
        raise RuntimeError("Transação não encontrada ou já finalizada — não é possível confirmar.")
    mensagem = {"acao": "confirmar", "confirma": confirma}
    proc.stdin.write(json.dumps(mensagem) + "\n")
    proc.stdin.flush()


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
                confirmar_pagamento_sitef(1, transacao_id=transacao_id)
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


# ── Funções administrativas/de teste interativas (Roteiro de Pré-Homologação
# Fiserv — Menu Administrativo 110 e, se necessário, qualquer outra função via
# o campo livre do painel) ─────────────────────────────────────────────────────
#
# Diferente de _executar_worker (que escreve o payload, fecha o stdin e espera
# o processo terminar), aqui o stdin do subprocesso permanece ABERTO enquanto
# a função roda: o operador responde aos prompts (menu, sim/não, dado, senha
# mascarada) pelo painel admin, e cada resposta é escrita no stdin do processo
# já em execução — por isso o registro _processos_ativos por execucao_id.

_processos_ativos: Dict[str, subprocess.Popen] = {}
_processos_lock = threading.Lock()


def _log_mensagem_worker(execucao_id: str, mensagem: dict) -> None:
    sessao = homolog_store.obter(execucao_id)
    tipo_prompt = sessao.prompt_pendente.get("tipo") if sessao and sessao.prompt_pendente else None
    sensivel = tipo_prompt in ("senha_supervisor", "campo_mascarado")
    valor_log = "***" if sensivel else mensagem.get("valor")
    logger.info("[Homologacao][%s] resposta operador (tipo=%s): %r", execucao_id[:8], tipo_prompt, valor_log)


def iniciar_funcao_administrativa_async(funcao_codigo: str, cnpj_estabelecimento: str = "") -> str:
    """Inicia uma função administrativa/de teste CliSiTef em subprocesso,
    mantendo o stdin aberto para o operador responder aos prompts via painel
    admin. Retorna o execucao_id para polling de status."""
    sessao = homolog_store.criar(funcao=funcao_codigo)
    execucao_id = sessao.execucao_id

    payload = {
        "modo": "funcao_admin",
        "funcao_codigo": funcao_codigo,
        "cnpj_estabelecimento": cnpj_estabelecimento,
    }
    worker_cmd = comando_worker_sitef()
    logger.info("[Homologacao][%s] iniciando função %s", execucao_id[:8], funcao_codigo)

    proc = subprocess.Popen(
        worker_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_env_base(),
    )
    proc.stdin.write(json.dumps(payload) + "\n")
    proc.stdin.flush()

    with _processos_lock:
        _processos_ativos[execucao_id] = proc

    def _drain_stderr() -> None:
        assert proc.stderr is not None
        for line in proc.stderr:
            line = line.rstrip("\n")
            if not line:
                continue
            if line.startswith("{"):
                try:
                    evento = json.loads(line)
                except json.JSONDecodeError:
                    continue
                homolog_store.atualizar_evento(execucao_id, evento)
                logger.info("[Homologacao][%s] %s", execucao_id[:8], line)
            else:
                logger.warning("[Homologacao worker] %s", line)

    def _run() -> None:
        stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
        stderr_thread.start()

        stdout_lines: list[str] = []
        assert proc.stdout is not None
        for line in proc.stdout:
            stdout_lines.append(line.rstrip("\n"))

        proc.wait()
        stderr_thread.join(timeout=5)

        with _processos_lock:
            _processos_ativos.pop(execucao_id, None)

        # O evento "finalizada" já é emitido via stderr por
        # executar_funcao_administrativa — isso só cobre falha total antes de
        # qualquer evento (ex.: erro ao carregar a lib, IniciaFuncao falhou).
        sessao_atual = homolog_store.obter(execucao_id)
        if sessao_atual and sessao_atual.status == "processando":
            stdout = "\n".join(stdout_lines).strip()
            resultado = None
            if stdout:
                try:
                    resultado = json.loads(stdout.splitlines()[-1])
                except json.JSONDecodeError:
                    resultado = None
            erro = (resultado or {}).get("erro") if resultado else None
            homolog_store.finalizar_com_erro(
                execucao_id, erro or "sitef_worker encerrou sem finalizar a função"
            )

    threading.Thread(target=_run, daemon=True).start()
    return execucao_id


def responder_prompt_funcao_admin(execucao_id: str, valor: str) -> None:
    """Envia a resposta do operador (menu, sim/não, dado, senha mascarada)
    para o subprocesso em execução, via stdin — nunca loga o valor cru
    (pode ser senha de supervisor)."""
    with _processos_lock:
        proc = _processos_ativos.get(execucao_id)
    if not proc or proc.stdin is None or proc.stdin.closed:
        raise RuntimeError("Execução não encontrada ou já finalizada.")

    mensagem = {"acao": "responder_prompt", "valor": valor}
    _log_mensagem_worker(execucao_id, mensagem)
    proc.stdin.write(json.dumps(mensagem) + "\n")
    proc.stdin.flush()


def obter_status_funcao_admin(execucao_id: str) -> Optional[dict]:
    sessao = homolog_store.obter(execucao_id)
    if not sessao:
        return None
    return sessao.to_dict()
