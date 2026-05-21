#!/usr/bin/env python3
"""
sitef_worker.py — executado como subprocesso pelo sitef_service.
Lê um JSON de stdin, executa a transação SiTef e escreve o resultado em stdout.

Protocolo:
  stdin  → JSON com { funcao, valor_reais, cupom }
  stdout → JSON com o resultado da transação
  stderr → logs
  exit 0 → OK, exit 1 → erro
"""

import ctypes
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
                    format="[sitef_worker] %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── Configuração ─────────────────────────────────────────────────────────────

SITEF_IP          = os.getenv("SITEF_IP",          "192.168.10.50")
SITEF_ID_LOJA     = os.getenv("SITEF_ID_LOJA",     "00000000")
SITEF_ID_TERMINAL = os.getenv("SITEF_ID_TERMINAL", "ST000001")
SITEF_OPERADOR    = os.getenv("SITEF_OPERADOR",    "01")
BUFFER_SIZE       = 32768

SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "script"
LIB_PATH   = SCRIPT_DIR / "libclisitef.so"

# ─── Utilitários ──────────────────────────────────────────────────────────────

def _b(s: str) -> bytes:
    return s.encode("latin-1")

def _dec(raw: bytes) -> str:
    s = raw.decode("latin-1", errors="replace").rstrip("\x00").strip()
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1]
    return s

def _mk_buf(size: int = 8) -> ctypes.Array:
    return ctypes.create_string_buffer(size)

def _ascii_resultado(buf) -> int:
    try:
        return int(_dec(buf.raw).strip() or "0")
    except ValueError:
        return -999

def _zerar(buf) -> None:
    ctypes.memmove(ctypes.addressof(buf), b"\x00" * len(buf), len(buf))

def _responder(buf, valor: str) -> None:
    _zerar(buf)
    if valor:
        buf.value = f"{{{valor}}}".encode("latin-1")

def _selecionar_menu_cartao(msg: str) -> str:
    """
    Dado o texto do menu SiTef (ex: '1:Cheque;2:Cartao de Debito;3:Cartao de Credito;...'),
    retorna o índice (string) da primeira opção de cartão de débito/crédito.
    Evita selecionar Cheque (requer dados manuais).
    Fallback: primeira opção disponível que não seja cheque.
    """
    prioridade = ["debito", "debito", "credito", "cartao"]
    opcoes = [o.strip() for o in msg.split(";") if o.strip()]
    # Tenta encontrar opção de débito primeiro, depois crédito
    for keyword in ["debito", "credito", "cartao"]:
        for opcao in opcoes:
            partes = opcao.split(":", 1)
            if len(partes) == 2:
                idx, label = partes[0].strip(), partes[1].strip().lower()
                if keyword in label and "cheque" not in label:
                    return idx
    # Fallback: qualquer opção que não seja cheque
    for opcao in opcoes:
        partes = opcao.split(":", 1)
        if len(partes) == 2:
            idx, label = partes[0].strip(), partes[1].strip().lower()
            if "cheque" not in label:
                return idx
    # Último recurso: primeira opção
    if opcoes:
        return opcoes[0].split(":", 1)[0].strip()
    return "1"

# ─── Carregar lib ─────────────────────────────────────────────────────────────

def _carregar_lib() -> ctypes.CDLL:
    if not LIB_PATH.exists():
        raise FileNotFoundError(f"libclisitef.so não encontrada em: {LIB_PATH}")

    os.chdir(str(SCRIPT_DIR))

    for dep in ("libcurl64.so", "libemv64.so", "libqrencode64.so"):
        dep_path = SCRIPT_DIR / dep
        if dep_path.exists():
            ctypes.CDLL(str(dep_path), mode=ctypes.RTLD_GLOBAL)

    lib = ctypes.CDLL(str(LIB_PATH))
    _pchar = ctypes.POINTER(ctypes.c_char)

    lib.ConfiguraIntSiTefInterativoA.restype  = None
    lib.ConfiguraIntSiTefInterativoA.argtypes = [
        _pchar, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
    ]

    lib.IniciaFuncaoSiTefInterativoA.restype  = None
    lib.IniciaFuncaoSiTefInterativoA.argtypes = [
        _pchar, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
        ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
    ]

    lib.ContinuaFuncaoSiTefInterativoA.restype  = None
    lib.ContinuaFuncaoSiTefInterativoA.argtypes = [
        _pchar, _pchar, _pchar, _pchar, _pchar, _pchar, _pchar, _pchar,
    ]

    lib.FinalizaFuncaoSiTefInterativoA.restype  = None
    lib.FinalizaFuncaoSiTefInterativoA.argtypes = [_pchar, _pchar]

    logger.info("libclisitef.so carregada de %s", LIB_PATH)
    return lib

# ─── Loop de transação ────────────────────────────────────────────────────────

def _executar_loop(lib) -> tuple:
    buf_resultado = _mk_buf(8)
    buf_cmd       = _mk_buf(14)
    buf_tc        = _mk_buf(14)
    buf_min       = _mk_buf(8)
    buf_max       = _mk_buf(8)
    continua      = ctypes.create_string_buffer(b"000000", 8)
    buffer        = ctypes.create_string_buffer(BUFFER_SIZE)
    buf_tam       = ctypes.create_string_buffer(_b(str(BUFFER_SIZE).rjust(6, "0")), 8)

    dados: dict        = {}
    linhas_cupom: list = []

    while True:
        continua.value = b"000000"
        buf_tam.value  = _b(str(BUFFER_SIZE).rjust(6, "0"))

        lib.ContinuaFuncaoSiTefInterativoA(
            buf_resultado, buf_cmd, buf_tc, buf_min, buf_max,
            buffer, buf_tam, continua,
        )

        ret = _ascii_resultado(buf_resultado)
        if ret != 10000:
            return ret, dados, linhas_cupom

        c   = _ascii_resultado(buf_cmd)
        tc  = _ascii_resultado(buf_tc)
        msg = _dec(buffer.raw)

        logger.debug("cmd=%d tc=%d msg=%r", c, tc, msg[:80])

        # Armazena campos c=0 — NÃO modifica buffer
        if c == 0:
            if msg:
                dados[tc] = msg
            if tc in (121, 122):
                linhas_cupom.append(msg)
            continue

        # Mensagens informativas
        if c in (1, 2, 3, 52):
            if msg:
                logger.info("MSG cmd=%d tc=%d: %s", c, tc, msg)
            buffer.value = b""

        # Limpar displays
        elif c in (4, 11, 12, 13, 14, 15, 16):
            buffer.value = b""

        # SIM/NÃO — confirma automaticamente
        elif c == 20:
            logger.info("SIM/NÃO — auto-confirmando SIM")
            _responder(buffer, "0")

        # Menu — tenta selecionar cartão (débito/crédito), nunca cheque
        elif c == 21:
            logger.info("Menu: %s", msg)
            escolha = _selecionar_menu_cartao(msg)
            logger.info("Menu — selecionando opção %s", escolha)
            _responder(buffer, escolha)

        # Aguardar tecla
        elif c == 22:
            _responder(buffer, "")

        # Periférico — sem delay
        elif c == 23:
            _zerar(buffer)

        # Campo silencioso (forma de pagamento): à vista
        elif c == 29:
            logger.info("Forma pagto silenciosa — enviando 1 (à vista)")
            _responder(buffer, "1")

        # Qualquer outro (pinpad gerencia)
        else:
            logger.debug("cmd=%d — enviando vazio (pinpad gerencia)", c)
            _responder(buffer, "")

# ─── Transação principal ──────────────────────────────────────────────────────

def executar(funcao: int, valor_reais: str, cupom: str) -> dict:
    lib = _carregar_lib()

    # Configura
    resultado = _mk_buf(8)
    lib.ConfiguraIntSiTefInterativoA(
        resultado,
        _b(SITEF_IP),
        _b(SITEF_ID_LOJA.ljust(8)),
        _b(SITEF_ID_TERMINAL.ljust(8)),
        _b("000000"),
    )
    ret_cfg = _ascii_resultado(resultado)
    logger.info("ConfiguraInt → %d", ret_cfg)
    if ret_cfg != 0:
        raise RuntimeError(f"ConfiguraInt falhou: {ret_cfg}")

    data = datetime.now().strftime("%Y%m%d")
    hora = datetime.now().strftime("%H%M%S")

    # Inicia
    resultado2 = _mk_buf(8)
    lib.IniciaFuncaoSiTefInterativoA(
        resultado2,
        _b(str(funcao).rjust(6, "0")),
        _b(valor_reais),
        _b(cupom),
        _b(data),
        _b(hora),
        _b(SITEF_OPERADOR),
        _b(""),
    )
    ret_inicia = _ascii_resultado(resultado2)
    logger.info("IniciaFuncao(%d, %s) → %d", funcao, valor_reais, ret_inicia)

    if ret_inicia != 10000:
        raise RuntimeError(f"IniciaFuncaoSiTef falhou: {ret_inicia}")

    # Loop
    ret_loop, dados, linhas_cupom = _executar_loop(lib)
    logger.info("Loop finalizado: ret=%d aprovada=%s", ret_loop, ret_loop == 0)

    # Monta resultado ANTES do Finaliza — se a lib crashar no Finaliza,
    # o JSON já foi emitido e o serviço consegue ler (padrão do test_clisitef)
    resultado = {
        "aprovada":     ret_loop == 0,
        "resultado":    ret_loop,
        "cupom":        cupom,
        "nsu_sitef":    dados.get(133, ""),
        "nsu_host":     dados.get(134, ""),
        "autorizacao":  dados.get(135, ""),
        "modalidade":   dados.get(101, ""),
        "bandeira":     dados.get(156, ""),
        "dados":        {str(k): v for k, v in dados.items()},
        "linhas_cupom": linhas_cupom,
    }
    # Emite o JSON imediatamente (flush garante que chega ao pai antes de qualquer crash)
    sys.stdout.write(json.dumps(resultado) + "\n")
    sys.stdout.flush()

    # Finaliza — sempre chamado; pode crashar em estados de erro internos da lib
    confirma = 1 if ret_loop == 0 else 0
    resultado_fin = _mk_buf(8)
    confirma_buf  = ctypes.create_string_buffer(_b(str(confirma).rjust(6, "0")), 8)
    lib.FinalizaFuncaoSiTefInterativoA(resultado_fin, confirma_buf)
    ret_fin = _ascii_resultado(resultado_fin)
    logger.info("FinalizaFuncao(confirma=%d) → %d", confirma, ret_fin)

    return resultado

# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        payload = json.loads(sys.stdin.read())
        executar(
            funcao=int(payload["funcao"]),
            valor_reais=str(payload["valor_reais"]),
            cupom=str(payload["cupom"]),
        )
        sys.exit(0)
    except Exception as exc:
        logger.error("Erro fatal: %s", exc, exc_info=True)
        # Emite JSON de erro apenas se ainda não foi emitido resultado
        sys.stdout.write(json.dumps({"erro": str(exc)}) + "\n")
        sys.stdout.flush()
        sys.exit(1)

