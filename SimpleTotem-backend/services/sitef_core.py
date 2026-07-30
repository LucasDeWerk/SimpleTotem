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

from core.config import (
    SCRIPT_DIR,
    SITEF_IP,
    SITEF_ID_LOJA,
    SITEF_ID_TERMINAL,
    SITEF_OPERADOR,
    SITEF_CNPJ_AUTOMACAO,
    SITEF_PORTA_PINPAD,
    SITEF_TLS_TOKEN,
    SITEF_SUPERVISOR_SENHA,
)

logger = logging.getLogger(__name__)

LIB_PATH = SCRIPT_DIR / "libclisitef.so"
_INI_PATH = SCRIPT_DIR / "CliSiTef.ini"
BUFFER_SIZE = 32768


def atualizar_porta_pinpad(porta: str) -> None:
    """Atualiza a porta do pinpad em CliSiTef.ini preservando todo o restante do arquivo."""
    porta = porta.strip()
    if not porta:
        return

    if not _INI_PATH.exists():
        _INI_PATH.write_text(f"[PinPadCompartilhado]\nPorta={porta}\n", encoding="latin-1")
        logger.info("CliSiTef.ini criado com Porta=%s", porta)
        return

    linhas = _INI_PATH.read_text(encoding="latin-1").splitlines(keepends=True)
    em_secao = False
    porta_escrita = False
    resultado: list[str] = []

    for linha in linhas:
        stripped = linha.strip()
        if stripped.startswith("["):
            if em_secao and not porta_escrita:
                resultado.append(f"Porta={porta}\n")
                porta_escrita = True
            em_secao = stripped == "[PinPadCompartilhado]"

        if em_secao and stripped.lower().startswith("porta="):
            resultado.append(f"Porta={porta}\n")
            porta_escrita = True
            continue

        resultado.append(linha)

    if em_secao and not porta_escrita:
        resultado.append(f"Porta={porta}\n")
        porta_escrita = True

    if not porta_escrita:
        resultado.append(f"\n[PinPadCompartilhado]\nPorta={porta}\n")

    _INI_PATH.write_text("".join(resultado), encoding="latin-1")
    logger.info("CliSiTef.ini atualizado: Porta=%s", porta)

EventCallback = Optional[Callable[[dict], None]]


def _b(s: str) -> bytes:
    return s.encode("latin-1")


def _dec(raw: bytes) -> str:
    """Decodifica buffer CliSiTef removendo NUL, espaços de padding e delimitadores externos."""
    nul = raw.find(b"\x00")
    if nul >= 0:
        raw = raw[:nul]
    # strip() antes de checar delimitadores: buffers chegam preenchidos com espaços
    s = raw.decode("latin-1", errors="replace").strip()
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
    """Formato VRS-248: [ParmsClient=1=...;2=...;][TransacoesAdicionaisHabilitadas=7;][TipoComunicacaoExterna=...]"""
    cnpj1 = _normalizar_cnpj(cnpj_estabelecimento)
    cnpj2 = _normalizar_cnpj(cnpj_automacao or SITEF_CNPJ_AUTOMACAO)
    parms = (
        f"[ParmsClient=1={cnpj1};2={cnpj2};]"
        f"[TransacoesAdicionaisHabilitadas=7;]"
    )
    if SITEF_TLS_TOKEN:
        parms += f"[TipoComunicacaoExterna=TLSGWP;TokenRegistro={SITEF_TLS_TOKEN}]"
    return parms


def _norm(texto: str) -> str:
    """Remove acentos e passa para minúsculo para comparação."""
    import unicodedata
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


def _selecionar_menu(msg: str, funcao: int) -> str:
    opcoes = [o.strip() for o in msg.split(";") if o.strip()]

    def partes_de(opcao):
        p = opcao.split(":", 1)
        return (p[0].strip(), _norm(p[1])) if len(p) == 2 else (None, None)

    # PIX / Carteira Digital → procura label específica
    if funcao == 122:
        for opcao in opcoes:
            idx, label = partes_de(opcao)
            if idx and any(k in label for k in ("pix", "carteira", "digital", "qr")):
                return idx

    # Crédito (2) e Débito (3) → "A Vista" é sempre a opção certa para pagamento simples
    if funcao in (2, 3, 0):
        for opcao in opcoes:
            idx, label = partes_de(opcao)
            if idx and any(k in label for k in ("a vista", "avista", "vista")):
                return idx

    # Fallback: palavras-chave genéricas
    for keyword in ("debito", "credito", "cartao", "pix"):
        for opcao in opcoes:
            idx, label = partes_de(opcao)
            if idx and keyword in label and "cheque" not in label:
                return idx

    # Última opção: primeira entrada que não seja cheque
    for opcao in opcoes:
        idx, label = partes_de(opcao)
        if idx and "cheque" not in (label or ""):
            return idx

    return opcoes[0].split(":", 1)[0].strip() if opcoes else "1"


def carregar_lib() -> ctypes.CDLL:
    if not LIB_PATH.exists():
        raise FileNotFoundError(f"libclisitef.so não encontrada em: {LIB_PATH}")

    # Se o INI não tiver [PinPadCompartilhado], usa o valor do .env como padrão inicial
    if not _INI_PATH.exists() or "[PinPadCompartilhado]" not in _INI_PATH.read_text(encoding="latin-1"):
        atualizar_porta_pinpad(SITEF_PORTA_PINPAD)

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


def _executar_loop(
    lib,
    funcao: int,
    on_event: EventCallback,
    valor_str: str = "0",
    num_parcelas: int = 1,
) -> tuple[int, dict, list]:
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

        if c in (1, 2, 3) and tc == 500:
            # SiTef solicitando senha do supervisor (funções administrativas)
            _responder(buffer, SITEF_SUPERVISOR_SENHA)
            _emit_event(on_event, "mensagem", texto="[Autenticação de supervisor]", destino="operador", tipo_campo=500)

        elif c in (1, 2, 3):
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
            # Se o SiTef pedir número de parcelas e já tivermos o valor, responde automaticamente
            if num_parcelas > 1 and tc in (7, 8, 9, 14, 800):
                _responder(buffer, str(num_parcelas))
                _emit_event(on_event, "mensagem", texto=f"Parcelas: {num_parcelas}", destino="operador", tipo_campo=tc)
            else:
                _zerar(buffer)

        elif c == 29:
            _responder(buffer, "1")

        elif c == 34:
            # Coleta de valor monetário — devolve centavos como string inteira
            _responder(buffer, valor_str)
            _emit_event(on_event, "mensagem", texto=msg or valor_str, destino="valor", tipo_campo=tc)

        else:
            logger.debug("cmd=%d — resposta vazia", c)
            _responder(buffer, "")


def gerar_cupom_fiscal() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")


def executar_transacao(
    funcao: int,
    valor_centavos: int,
    cupom: str,
    cnpj_estabelecimento: str = "",
    on_event: EventCallback = None,
    restricao: str = "",
    num_parcelas: int = 1,
) -> dict:
    lib = carregar_lib()
    configurar(lib, cnpj_estabelecimento, on_event)

    data = datetime.now().strftime("%Y%m%d")
    hora = datetime.now().strftime("%H%M%S")

    # A lib lê Valor como string delimitada por {}: "{34,90}"
    # ffae5 extrai o conteúdo entre o primeiro char (abre) e seu par (fecha):
    #   '{' → '}',  '[' → ']',  etc.
    # Sem as chaves, o primeiro dígito ("3") vira delimitador, o restante ("4,90")
    # é lido como conteúdo → bug confirmado no pinpad.
    valor_display = f"{valor_centavos // 100},{valor_centavos % 100:02d}"
    valor_str = f"{{{valor_display}}}"   # "{34,90}"

    print(
        f"[sitef_core] IniciaFuncao funcao={funcao}  "
        f"valor_centavos={valor_centavos}  valor_str(→lib)={valor_str!r}",
        file=sys.stderr, flush=True,
    )
    logger.info("IniciaFuncao(%d, %s, cupom=%s)", funcao, valor_str, cupom)

    resultado2 = _mk_buf(8)
    lib.IniciaFuncaoSiTefInterativoA(
        resultado2,
        _b(str(funcao).rjust(6, "0")),
        _b(valor_str),
        _b(cupom),
        _b(data),
        _b(hora),
        _b(SITEF_OPERADOR),
        _b(restricao),
    )
    ret_inicia = _ascii_resultado(resultado2)
    logger.info("IniciaFuncao → %d (restricao=%r, parcelas=%d)", ret_inicia, restricao, num_parcelas)
    _emit_event(on_event, "iniciada", funcao=funcao, valor=valor_display, cupom=cupom)

    if ret_inicia != 10000:
        raise RuntimeError(f"IniciaFuncaoSiTef falhou: {ret_inicia}")

    ret_loop, dados, linhas_cupom = _executar_loop(lib, funcao, on_event, valor_str, num_parcelas)
    if not linhas_cupom:
        linhas_cupom = _resolver_cupom_bruto([], [], dados, valor_display)
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

    # Se negada: finaliza imediatamente com confirma=0 (nada a confirmar)
    # Se aprovada: deixa pendente — o backend chamará FinalizaFuncaoSiTefInterativoA
    # somente APÓS impressão do cupom TEF e emissão do XML fiscal (Item 8.1.1 CliSiTef AA)
    resultado["pendente_confirmacao"] = ret_loop == 0
    if ret_loop != 0:
        resultado_fin = _mk_buf(8)
        confirma_buf = ctypes.create_string_buffer(_b("000000"), 8)
        lib.FinalizaFuncaoSiTefInterativoA(resultado_fin, confirma_buf)
        resultado["pendente_confirmacao"] = False

    _emit_event(
        on_event,
        "finalizada",
        aprovada=resultado["aprovada"],
        resultado=ret_loop,
        mensagem=dados.get(-1, "") or dados.get(0, ""),
    )
    return resultado


def confirmar_transacao(confirma: int, on_event: EventCallback = None) -> None:
    """
    Finaliza a transação SiTef após impressão do cupom TEF e emissão do XML fiscal.
    Deve ser chamada pelo backend somente após esses dois passos (Item 8.1.1).
    confirma=1 → confirma (pagamento OK, comprovante impresso)
    confirma=0 → desfaz (falha na impressão ou no XML)
    """
    lib = carregar_lib()
    resultado_fin = _mk_buf(8)
    confirma_buf = ctypes.create_string_buffer(_b(str(confirma).rjust(6, "0")), 8)
    lib.FinalizaFuncaoSiTefInterativoA(resultado_fin, confirma_buf)
    _emit_event(on_event, "confirmacao_enviada", confirma=confirma)


def cancelar_transacao(
    valor_centavos: int,
    cupom_original: str,
    data_original: str,
    nsu_host: str,
    cnpj_estabelecimento: str = "",
    on_event: EventCallback = None,
) -> dict:
    """
    Cancelamento via função SiTef 123 (cancelamento direto).
    data_original: AAAAMMDD da transação original.
    nsu_host: NSU do host retornado na transação original.
    """
    lib = carregar_lib()
    configurar(lib, cnpj_estabelecimento, on_event)

    data = datetime.now().strftime("%Y%m%d")
    hora = datetime.now().strftime("%H%M%S")
    cupom_cancelamento = gerar_cupom_fiscal()

    valor_display = f"{valor_centavos // 100},{valor_centavos % 100:02d}"
    valor_str = f"{{{valor_display}}}"

    logger.info(
        "cancelar_transacao: funcao=123 valor=%s cupom_orig=%s data_orig=%s nsu_host=%s",
        valor_str, cupom_original, data_original, nsu_host,
    )

    resultado2 = _mk_buf(8)
    lib.IniciaFuncaoSiTefInterativoA(
        resultado2,
        _b("000123"),
        _b(valor_str),
        _b(cupom_cancelamento),
        _b(data),
        _b(hora),
        _b(SITEF_OPERADOR),
        _b(""),
    )
    ret_inicia = _ascii_resultado(resultado2)
    logger.info("IniciaFuncao cancelamento → %d", ret_inicia)

    if ret_inicia != 10000:
        raise RuntimeError(f"IniciaFuncao cancelamento falhou: {ret_inicia}")

    _emit_event(on_event, "iniciada", funcao=123, valor=valor_display, cupom=cupom_cancelamento)

    # Loop que responde automaticamente aos campos de cancelamento
    ret_loop, dados, linhas_cupom = _executar_loop_cancelamento(
        lib, on_event,
        valor_str=valor_str,
        nsu_host=nsu_host,
        data_original=data_original,
    )

    if not linhas_cupom:
        linhas_cupom = _resolver_cupom_bruto([], [], dados, valor_display)
    cupom_bruto = _cupom_bruto_texto(linhas_cupom)

    resultado = {
        "aprovada": ret_loop == 0,
        "resultado": ret_loop,
        "nsu_sitef": dados.get(133, ""),
        "nsu_host": dados.get(134, ""),
        "cupom_bruto": cupom_bruto,
        "linhas_cupom": linhas_cupom,
    }

    confirma = 1 if ret_loop == 0 else 0
    resultado_fin = _mk_buf(8)
    confirma_buf = ctypes.create_string_buffer(_b(str(confirma).rjust(6, "0")), 8)
    lib.FinalizaFuncaoSiTefInterativoA(resultado_fin, confirma_buf)

    _emit_event(on_event, "finalizada", aprovada=resultado["aprovada"], resultado=ret_loop)

    sys.stdout.write(json.dumps(resultado, ensure_ascii=False) + "\n")
    sys.stdout.flush()

    return resultado


def _executar_loop_cancelamento(
    lib,
    on_event: EventCallback,
    valor_str: str,
    nsu_host: str,
    data_original: str,
) -> tuple[int, dict, list]:
    """
    Loop igual ao principal, mas responde automaticamente a:
    - c==34 (valor monetário) → valor_str
    - c==23 com tc de documento/NSU → nsu_host
    - c==23 com tc de data → data_original
    """
    buf_resultado = _mk_buf(8)
    buf_cmd = _mk_buf(14)
    buf_tc = _mk_buf(14)
    buf_min = _mk_buf(8)
    buf_max = _mk_buf(8)
    continua = ctypes.create_string_buffer(b"000000", 8)
    buffer = ctypes.create_string_buffer(BUFFER_SIZE)
    buf_tam = ctypes.create_string_buffer(_b(str(BUFFER_SIZE).rjust(6, "0")), 8)

    # TCs conhecidos para documento/NSU no cancelamento
    _TC_DOCUMENTO = frozenset({13, 14, 15, 23, 133, 134})
    # TCs conhecidos para data no cancelamento
    _TC_DATA = frozenset({12, 17, 19, 45})

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
            return ret, dados, linhas_cupom

        c = _ascii_resultado(buf_cmd)
        tc = _ascii_resultado(buf_tc)
        msg = _dec(buffer.raw)

        logger.debug("cancelamento cmd=%d tc=%d msg=%r", c, tc, msg[:80] if msg else "")

        if c == 0:
            if msg:
                _registrar_dado(dados, tc, msg)
            if tc in _TC_CUPOM_CLIENTE:
                _append_cupom_bruto(cupom_cliente, msg)
            elif tc in _TC_CUPOM_LOJA:
                _append_cupom_bruto(cupom_loja, msg)
            continue

        if c in (1, 2, 3) and tc == 500:
            _responder(buffer, SITEF_SUPERVISOR_SENHA)
            _emit_event(on_event, "mensagem", texto="[Autenticação de supervisor]", destino="operador", tipo_campo=500)

        elif c in (1, 2, 3):
            if msg:
                destino = {1: "operador", 2: "cliente", 3: "ambos"}.get(c, "info")
                _emit_event(on_event, "mensagem", texto=msg, destino=destino, tipo_campo=tc)
            buffer.value = b""

        elif c == 34:
            _responder(buffer, valor_str)

        elif c == 23:
            if tc in _TC_DOCUMENTO and nsu_host:
                _responder(buffer, nsu_host)
            elif tc in _TC_DATA and data_original:
                _responder(buffer, data_original)
            else:
                _zerar(buffer)

        elif c == 21:
            escolha = _selecionar_menu(msg, 123)
            _emit_event(on_event, "menu", opcoes=msg, selecionado=escolha)
            _responder(buffer, escolha)

        elif c == 20:
            _responder(buffer, "0")

        elif c == 22:
            _responder(buffer, "")

        elif c == 29:
            _responder(buffer, "1")

        elif c in (4, 11, 12, 13, 14, 15, 16, 50, 51, 52):
            buffer.value = b""

        else:
            _responder(buffer, "")


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
        _b("{0,00}"),
        _b(cupom),
        _b(data),
        _b(hora),
        _b(SITEF_OPERADOR),
        _b(""),
    )
    if _ascii_resultado(resultado2) != 10000:
        logger.warning("IniciaFuncao pendências (130) falhou")
        return qty

    ret_loop, _, _ = _executar_loop(lib, 130, on_event, "0")
    confirma = 1 if ret_loop == 0 else 0
    resultado_fin = _mk_buf(8)
    confirma_buf = ctypes.create_string_buffer(_b(str(confirma).rjust(6, "0")), 8)
    lib.FinalizaFuncaoSiTefInterativoA(resultado_fin, confirma_buf)

    logger.info("Pendências resolvidas: ret=%d", ret_loop)
    return qty
