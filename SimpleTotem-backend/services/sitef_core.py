"""
Núcleo CliSiTef — configuração, loop interativo, PIX (QR) e pendências.
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "script"
LIB_PATH = SCRIPT_DIR / "libclisitef.so"
BUFFER_SIZE = 32768

SITEF_IP = os.getenv("SITEF_IP", "192.168.10.12")
SITEF_ID_LOJA = os.getenv("SITEF_ID_LOJA", "00000000")
SITEF_ID_TERMINAL = os.getenv("SITEF_ID_TERMINAL", "ST000001")
SITEF_OPERADOR = os.getenv("SITEF_OPERADOR", "01")
SITEF_CNPJ_AUTOMACAO = os.getenv("SITEF_CNPJ_AUTOMACAO", "12523654185985")

EventCallback = Optional[Callable[[dict], None]]


def _b(s: str) -> bytes:
    return s.encode("latin-1")


def _dec(raw: bytes) -> str:
    """Decodifica buffer CliSiTef removendo apenas NUL e delimitadores externos."""
    nul = raw.find(b"\x00")
    if nul >= 0:
        raw = raw[:nul]
    s = raw.decode("latin-1", errors="replace")
    if len(s) >= 2 and s[0] in "{([<" and s[-1] in "})]>" and s[0] != s[-1]:
        s = s[1:-1]
    elif s.startswith("{") and s.endswith("}"):
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


def _emit_event(cb: EventCallback, evento: str, **payload) -> None:
    data = {"evento": evento, **payload}
    if cb:
        cb(data)
    sys.stderr.write(json.dumps(data, ensure_ascii=False) + "\n")
    sys.stderr.flush()


def _normalizar_cnpj(valor: str) -> str:
    digitos = "".join(c for c in (valor or "") if c.isdigit())
    if len(digitos) != 14:
        raise ValueError(f"CNPJ inválido (precisa 14 dígitos): {valor!r}")
    return digitos


def _montar_parametros_adicionais(cnpj_estabelecimento: str, cnpj_automacao: str) -> str:
    """Formato VRS-248: [ParmsClient=1=...;2=...;][TransacoesAdicionaisHabilitadas=7;]"""
    cnpj1 = _normalizar_cnpj(cnpj_estabelecimento)
    cnpj2 = _normalizar_cnpj(cnpj_automacao or SITEF_CNPJ_AUTOMACAO)
    return (
        f"[ParmsClient=1={cnpj1};2={cnpj2};]"
        f"[TransacoesAdicionaisHabilitadas=7;]"
    )


def _selecionar_menu(msg: str, funcao: int) -> str:
    opcoes = [o.strip() for o in msg.split(";") if o.strip()]
    if funcao == 122:
        for opcao in opcoes:
            partes = opcao.split(":", 1)
            if len(partes) == 2:
                idx, label = partes[0].strip(), partes[1].strip().lower()
                if "pix" in label or "carteira" in label or "digital" in label or "qr" in label:
                    return idx
    for keyword in ["debito", "credito", "cartao", "pix"]:
        for opcao in opcoes:
            partes = opcao.split(":", 1)
            if len(partes) == 2:
                idx, label = partes[0].strip(), partes[1].strip().lower()
                if keyword in label and "cheque" not in label:
                    return idx
    for opcao in opcoes:
        partes = opcao.split(":", 1)
        if len(partes) == 2 and "cheque" not in partes[1].lower():
            return partes[0].strip()
    return opcoes[0].split(":", 1)[0].strip() if opcoes else "1"


def carregar_lib() -> ctypes.CDLL:
    if not LIB_PATH.exists():
        raise FileNotFoundError(f"libclisitef.so não encontrada em: {LIB_PATH}")

    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        from pinpad_config import garantir_configurado
        garantir_configurado()
    except ImportError:
        pass

    os.chdir(str(SCRIPT_DIR))

    for dep in ("libcurl64.so", "libemv64.so", "libqrencode64.so"):
        dep_path = SCRIPT_DIR / dep
        if dep_path.exists():
            ctypes.CDLL(str(dep_path), mode=ctypes.RTLD_GLOBAL)

    lib = ctypes.CDLL(str(LIB_PATH))
    _pchar = ctypes.POINTER(ctypes.c_char)

    lib.ConfiguraIntSiTefInterativoExA.restype = None
    lib.ConfiguraIntSiTefInterativoExA.argtypes = [
        _pchar, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
    ]
    lib.ConfiguraIntSiTefInterativoA.restype = None
    lib.ConfiguraIntSiTefInterativoA.argtypes = [
        _pchar, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
    ]
    lib.IniciaFuncaoSiTefInterativoA.restype = None
    lib.IniciaFuncaoSiTefInterativoA.argtypes = [
        _pchar, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
        ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
    ]
    lib.ContinuaFuncaoSiTefInterativoA.restype = None
    lib.ContinuaFuncaoSiTefInterativoA.argtypes = [
        _pchar, _pchar, _pchar, _pchar, _pchar, _pchar, _pchar, _pchar,
    ]
    lib.FinalizaFuncaoSiTefInterativoA.restype = None
    lib.FinalizaFuncaoSiTefInterativoA.argtypes = [_pchar, _pchar]
    lib.ObtemQuantidadeTransacoesPendentesA.restype = None
    lib.ObtemQuantidadeTransacoesPendentesA.argtypes = [_pchar, _pchar, _pchar]

    return lib


def configurar(lib, cnpj_estabelecimento: str = "", on_event: EventCallback = None) -> None:
    if not cnpj_estabelecimento:
        raise RuntimeError(
            "CNPJ do estabelecimento não configurado. Sincronize a empresa no banco."
        )
    parms = _montar_parametros_adicionais(cnpj_estabelecimento, SITEF_CNPJ_AUTOMACAO)
    resultado = _mk_buf(8)
    logger.info("ParametrosAdicionais: %s", parms)

    try:
        lib.ConfiguraIntSiTefInterativoExA(
            resultado,
            _b(SITEF_IP),
            _b(SITEF_ID_LOJA.ljust(8)),
            _b(SITEF_ID_TERMINAL.ljust(8)),
            _b("000000"),
            _b(parms),
        )
        ret = _ascii_resultado(resultado)
        logger.info("ConfiguraIntSiTefInterativoExA → %d", ret)
    except AttributeError:
        lib.ConfiguraIntSiTefInterativoA(
            resultado,
            _b(SITEF_IP),
            _b(SITEF_ID_LOJA.ljust(8)),
            _b(SITEF_ID_TERMINAL.ljust(8)),
            _b(parms),
        )
        ret = _ascii_resultado(resultado)
        logger.info("ConfiguraIntSiTefInterativoA (fallback) → %d", ret)

    if ret != 0:
        raise RuntimeError(f"ConfiguraInt falhou: {ret}")

    _emit_event(on_event, "configurado")


# TCs do comprovante TEF — via loja (122) tem prioridade no totem
_TC_CUPOM_LOJA = frozenset({122})
_TC_CUPOM_CLIENTE = frozenset({121})


def _append_cupom_bruto(destino: list, msg: str) -> None:
    """Acumula bloco exatamente como recebido do SiTef/Fiserv (sem quebras)."""
    if msg:
        destino.append(msg)


def _registrar_dado(dados: dict, tc: int, msg: str) -> None:
    """Guarda valor do TC; múltiplos TC 121/122 são acumulados (MultiplosCupons)."""
    if tc in (121, 122):
        atual = dados.get(tc)
        if atual is None:
            dados[tc] = msg
        elif isinstance(atual, list):
            atual.append(msg)
        else:
            dados[tc] = [atual, msg]
    else:
        dados[tc] = msg


def _extrair_cupom_bruto_de_dados(dados: dict, tcs: tuple) -> list:
    """Recupera blocos brutos TC 121/122 armazenados no loop."""
    blocos: list = []
    for tc in tcs:
        valor = dados.get(tc)
        if not valor:
            continue
        if isinstance(valor, list):
            blocos.extend(valor)
        else:
            blocos.append(str(valor))
    return blocos


def _montar_cupom_fallback(dados: dict, valor_reais: str = "") -> list:
    """Último recurso — um único bloco texto quando TC 121/122 não vierem."""
    partes: list = []
    for tc in (122, 121, 112, 102, 101):
        valor = dados.get(tc)
        if not valor:
            continue
        if isinstance(valor, list):
            partes.extend(valor)
        else:
            partes.append(str(valor))
    if valor_reais:
        partes.append(f"VALOR: R$ {valor_reais}")
    if dados.get(133):
        partes.append(f"NSU SiTef: {dados[133]}")
    if dados.get(134):
        partes.append(f"NSU Host: {dados[134]}")
    if dados.get(135):
        partes.append(f"AUT: {dados[135]}")
    if not partes:
        return []
    return ["\\".join(partes)]


def _resolver_cupom_bruto(
    cupom_loja: list,
    cupom_cliente: list,
    dados: dict,
    valor_reais: str = "",
) -> list:
    if cupom_loja:
        return list(cupom_loja)
    if cupom_cliente:
        return list(cupom_cliente)
    blocos = _extrair_cupom_bruto_de_dados(dados, (122, 121))
    if blocos:
        return blocos
    return _montar_cupom_fallback(dados, valor_reais)


def _cupom_bruto_texto(blocos: list) -> str:
    return "".join(blocos)


def _executar_loop(lib, funcao: int, on_event: EventCallback) -> tuple[int, dict, list]:
    buf_resultado = _mk_buf(8)
    buf_cmd = _mk_buf(14)
    buf_tc = _mk_buf(14)
    buf_min = _mk_buf(8)
    buf_max = _mk_buf(8)
    continua = ctypes.create_string_buffer(b"000000", 8)
    buffer = ctypes.create_string_buffer(BUFFER_SIZE)
    buf_tam = ctypes.create_string_buffer(_b(str(BUFFER_SIZE).rjust(6, "0")), 8)

    dados: dict = {}
    cupom_cliente: list = []
    cupom_loja: list = []

    while True:
        continua.value = b"000000"
        buf_tam.value = _b(str(BUFFER_SIZE).rjust(6, "0"))

        lib.ContinuaFuncaoSiTefInterativoA(
            buf_resultado, buf_cmd, buf_tc, buf_min, buf_max,
            buffer, buf_tam, continua,
        )

        ret = _ascii_resultado(buf_resultado)
        if ret != 10000:
            linhas_cupom = _resolver_cupom_bruto(cupom_loja, cupom_cliente, dados)
            logger.info(
                "Cupom bruto: %d bloco(s), %d chars (loja=%d cliente=%d)",
                len(linhas_cupom),
                len(_cupom_bruto_texto(linhas_cupom)),
                len(cupom_loja),
                len(cupom_cliente),
            )
            return ret, dados, linhas_cupom

        c = _ascii_resultado(buf_cmd)
        tc = _ascii_resultado(buf_tc)
        msg = _dec(buffer.raw)

        logger.debug("cmd=%d tc=%d msg=%r", c, tc, msg[:80] if msg else "")

        if c == 0:
            if msg:
                _registrar_dado(dados, tc, msg)
            if tc in _TC_CUPOM_CLIENTE:
                _append_cupom_bruto(cupom_cliente, msg)
                logger.info("TC %d via cliente: bloco %d chars", tc, len(msg))
            elif tc in _TC_CUPOM_LOJA:
                _append_cupom_bruto(cupom_loja, msg)
                logger.info("TC %d via loja: bloco %d chars", tc, len(msg))
            if tc == 584 and msg:
                _emit_event(on_event, "qrcode", payload=msg, tipo_campo=584)
            continue

        if c in (1, 2, 3):
            if msg:
                destino = {1: "operador", 2: "cliente", 3: "ambos"}.get(c, "info")
                _emit_event(on_event, "mensagem", texto=msg, destino=destino, tipo_campo=tc)
            buffer.value = b""

        elif c == 50:
            qrcode = msg or dados.get(584, "")
            if qrcode:
                _emit_event(on_event, "qrcode", payload=qrcode, tipo_campo=tc or 584)
            buffer.value = b""

        elif c == 51:
            _emit_event(on_event, "qrcode_remover")
            buffer.value = b""

        elif c == 52:
            if msg:
                _emit_event(on_event, "mensagem", texto=msg, destino="rodape", tipo_campo=tc or 4128)
            buffer.value = b""

        elif c in (4, 11, 12, 13, 14, 15, 16):
            buffer.value = b""

        elif c == 20:
            _emit_event(on_event, "mensagem", texto=msg or "Confirmar?", destino="confirmacao")
            _responder(buffer, "0")

        elif c == 21:
            escolha = _selecionar_menu(msg, funcao)
            _emit_event(on_event, "menu", opcoes=msg, selecionado=escolha)
            _responder(buffer, escolha)

        elif c == 22:
            _responder(buffer, "")

        elif c == 23:
            _zerar(buffer)

        elif c == 29:
            _responder(buffer, "1")

        else:
            logger.debug("cmd=%d — resposta vazia", c)
            _responder(buffer, "")


def gerar_cupom_fiscal() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")


def executar_transacao(
    funcao: int,
    valor_reais: str,
    cupom: str,
    cnpj_estabelecimento: str = "",
    on_event: EventCallback = None,
) -> dict:
    lib = carregar_lib()
    configurar(lib, cnpj_estabelecimento, on_event)

    data = datetime.now().strftime("%Y%m%d")
    hora = datetime.now().strftime("%H%M%S")

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
    logger.info("IniciaFuncao(%d, %s, cupom=%s) → %d", funcao, valor_reais, cupom, ret_inicia)
    _emit_event(on_event, "iniciada", funcao=funcao, valor=valor_reais, cupom=cupom)

    if ret_inicia != 10000:
        raise RuntimeError(f"IniciaFuncaoSiTef falhou: {ret_inicia}")

    ret_loop, dados, linhas_cupom = _executar_loop(lib, funcao, on_event)
    if not linhas_cupom:
        linhas_cupom = _resolver_cupom_bruto([], [], dados, valor_reais)
    cupom_bruto = _cupom_bruto_texto(linhas_cupom)
    logger.info(
        "Loop finalizado: ret=%d aprovada=%s blocos=%d chars=%d",
        ret_loop, ret_loop == 0, len(linhas_cupom), len(cupom_bruto),
    )

    resultado = {
        "aprovada": ret_loop == 0,
        "resultado": ret_loop,
        "cupom": cupom,
        "nsu_sitef": dados.get(133, ""),
        "nsu_host": dados.get(134, ""),
        "autorizacao": dados.get(135, ""),
        "modalidade": dados.get(101, ""),
        "bandeira": dados.get(156, ""),
        "dados": {str(k): v for k, v in dados.items()},
        "linhas_cupom": linhas_cupom,
        "cupom_bruto": cupom_bruto,
        "pix": funcao == 122,
    }

    sys.stdout.write(json.dumps(resultado, ensure_ascii=False) + "\n")
    sys.stdout.flush()

    confirma = 1 if ret_loop == 0 else 0
    resultado_fin = _mk_buf(8)
    confirma_buf = ctypes.create_string_buffer(_b(str(confirma).rjust(6, "0")), 8)
    lib.FinalizaFuncaoSiTefInterativoA(resultado_fin, confirma_buf)

    _emit_event(
        on_event,
        "finalizada",
        aprovada=resultado["aprovada"],
        resultado=ret_loop,
        mensagem=dados.get(-1, "") or dados.get(0, ""),
    )
    return resultado


def resolver_pendencias(cnpj_estabelecimento: str = "", on_event: EventCallback = None) -> int:
    """Resolve transações pendentes (função 130) na inicialização."""
    lib = carregar_lib()
    configurar(lib, cnpj_estabelecimento, on_event)

    data = datetime.now().strftime("%Y%m%d")
    cupom = gerar_cupom_fiscal()

    resultado = _mk_buf(8)
    buf_cupom = ctypes.create_string_buffer(_b(cupom), len(cupom) + 2)
    buf_data = ctypes.create_string_buffer(_b(data), len(data) + 2)
    lib.ObtemQuantidadeTransacoesPendentesA(resultado, buf_cupom, buf_data)
    qty = _ascii_resultado(resultado)

    logger.info("Pendências SiTef para cupom=%s data=%s → %d", cupom, data, qty)
    if qty in (-13, 0) or qty < 0:
        return 0

    _emit_event(on_event, "pendencias", quantidade=qty)

    resultado2 = _mk_buf(8)
    hora = datetime.now().strftime("%H%M%S")
    lib.IniciaFuncaoSiTefInterativoA(
        resultado2,
        _b("000130"),
        _b("0,00"),
        _b(cupom),
        _b(data),
        _b(hora),
        _b(SITEF_OPERADOR),
        _b(""),
    )
    if _ascii_resultado(resultado2) != 10000:
        logger.warning("IniciaFuncao pendências (130) falhou")
        return qty

    ret_loop, _, _ = _executar_loop(lib, 130, on_event)
    confirma = 1 if ret_loop == 0 else 0
    resultado_fin = _mk_buf(8)
    confirma_buf = ctypes.create_string_buffer(_b(str(confirma).rjust(6, "0")), 8)
    lib.FinalizaFuncaoSiTefInterativoA(resultado_fin, confirma_buf)

    logger.info("Pendências resolvidas: ret=%d", ret_loop)
    return qty
