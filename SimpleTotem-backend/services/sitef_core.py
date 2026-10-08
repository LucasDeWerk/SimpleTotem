"""
Núcleo CliSiTef — configuração, loop interativo, PIX (QR) e pendências.
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import select
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
from services.sitef_codigos import (
    descrever_erro_configura,
    descrever_erro_geral,
    formatar_codigo_configura,
    formatar_codigo_geral,
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


def _delim(valor: str) -> str:
    """Envolve o valor em {} para os parâmetros que a lib lê pelo helper
    interno ffae5 (Valor, NumeroCupom, Operador, Restricoes, ParamsAdicionais).

    Confirmado por desassembly da libclisitef.so: o ffae5 SEMPRE consome o 1o
    caractere como delimitador de abertura e devolve o conteúdo até o par
    correspondente. Sem as chaves, o cupom "20260811132111" era lido como
    delimitador '2' + conteúdo "0" — exatamente o "Cupom PDV = 0" que a Fiserv
    reportou, e o motivo do cupom "se repetir" em todas as transações.
    """
    return f"{{{valor}}}"


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


def _finalizar_funcao(
    lib, confirma: int, cupom: str, data: str, hora: str, parms: str = "",
) -> int:
    """FinalizaFuncaoSiTefInterativoA(Confirma, NumeroCupom, DataFiscal,
    HoraFiscal, ParametrosAdicionais) — os 5 parâmetros são obrigatórios.

    Chamar com menos argumentos deixa DataFiscal/HoraFiscal apontando para
    lixo na pilha; o wrapper "A" desreferencia esses ponteiros e o processo
    morre com SIGSEGV (crash nativo, sem traceback Python). Era a causa do 502
    em /vendas/confirmar e do "sitef_worker encerrou sem resultado" na
    resolução de pendências.

    Devolve o código de retorno da CliSiTef (0 = OK).
    """
    return lib.FinalizaFuncaoSiTefInterativoA(
        _b("1" if int(confirma) else "0"),
        _b(_delim(cupom)),
        _b(data),
        _b(hora),
        _b(_delim(parms)),
    )


def _emit_event(cb: EventCallback, evento: str, **payload) -> None:
    data = {"evento": evento, **payload}
    if cb:
        cb(data)
    sys.stderr.write(json.dumps(data, ensure_ascii=False) + "\n")
    sys.stderr.flush()


def _ler_mensagem_stdin(timeout: float = 0.0) -> Optional[dict]:
    """Lê uma mensagem JSON (uma linha) do stdin deste processo, vinda do
    backend (sitef_service.py), sem bloquear além de `timeout` segundos.
    timeout=0 → só verifica se já tem algo pronto, não espera. Usado pelas
    funções administrativas interativas (painel admin → subprocesso)."""
    try:
        prontos, _, _ = select.select([sys.stdin], [], [], timeout)
    except (OSError, ValueError):
        return None
    if not prontos:
        return None
    linha = sys.stdin.readline()
    if not linha:
        return None
    try:
        return json.loads(linha)
    except json.JSONDecodeError:
        return None


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


def _aguardar_confirmacao_cancelamento(
    on_event: EventCallback, mensagem: str, tc: int, timeout: float = 60.0,
) -> bool:
    """ANULA físico no pinpad dispara essa pergunta da CliSiTef (c==20,
    tc==5013, "Operacao Cancelada?") esperando confirmação de verdade — não
    pode ser respondida sozinha (Seq. 9 do roteiro Fiserv). Bloqueia via
    stdin (mesmo canal não-bloqueante usado nas funções administrativas,
    ver _ler_mensagem_stdin) até a tela do totem responder ou o timeout
    expirar. Sem resposta a tempo, mantém a transação em curso (mais seguro
    que cancelar sem confirmação explícita)."""
    _emit_event(on_event, "confirmar_cancelamento", mensagem=mensagem, tc=tc)
    resposta = _ler_mensagem_stdin(timeout=timeout)
    if resposta and resposta.get("acao") == "responder_cancelamento":
        confirma = bool(resposta.get("confirma"))
    else:
        logger.warning(
            "Timeout/sem resposta à confirmação de cancelamento (tc=%d) — mantendo transação em curso.", tc,
        )
        confirma = False
    _emit_event(on_event, "confirmacao_cancelamento_resolvida")
    return confirma


def _selecionar_menu(msg: str, funcao: int, restricao: str = "") -> str:
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

    # Crédito (3) e Débito (2): quando a automação pediu parcelamento
    # (TransacoesHabilitadas=27/39 em `restricao`), escolhe a opção do menu
    # correspondente — senão cai no padrão "A Vista" de sempre.
    if funcao in (2, 3, 0):
        if "TransacoesHabilitadas=27" in restricao:
            for opcao in opcoes:
                idx, label = partes_de(opcao)
                if idx and "estabelecimento" in label:
                    return idx
        elif "TransacoesHabilitadas=39" in restricao:
            for opcao in opcoes:
                idx, label = partes_de(opcao)
                if idx and "administradora" in label:
                    return idx

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
    # 5 parâmetros, todos string — confirmado por desassembly da libclisitef.so:
    # o prólogo salva rdi/rsi/rdx/rcx/r8 e trata os args 3 e 4 com len=8
    # (DataFiscal AAAAMMDD) e len=6 (HoraFiscal HHMMSS). Declarar só 2 fazia o
    # wrapper desreferenciar ponteiros inexistentes → SIGSEGV. Ver _finalizar_funcao.
    lib.FinalizaFuncaoSiTefInterativoA.restype = ctypes.c_int
    lib.FinalizaFuncaoSiTefInterativoA.argtypes = [ctypes.c_char_p] * 5
    lib.ObtemQuantidadeTransacoesPendentesA.restype = None
    lib.ObtemQuantidadeTransacoesPendentesA.argtypes = [_pchar, _pchar, _pchar]

    return lib


# CNPJ já configurado NESTE processo — evita reconfigurar a lib no meio de uma
# sessão (o confirmar roda no mesmo worker da transação; um
# ConfiguraIntSiTefInterativoExA extra ali é desnecessário e mexe no estado
# interno logo antes do FinalizaFuncaoSiTefInterativoA).
_CNPJ_CONFIGURADO: Optional[str] = None


def configurar(
    lib, cnpj_estabelecimento: str = "", on_event: EventCallback = None, forcar: bool = False,
) -> None:
    global _CNPJ_CONFIGURADO
    if not cnpj_estabelecimento:
        raise RuntimeError(
            "CNPJ do estabelecimento não configurado. Sincronize a empresa no banco."
        )
    if not forcar and _CNPJ_CONFIGURADO == cnpj_estabelecimento:
        logger.info("ConfiguraInt já feito neste processo (CNPJ igual) — reaproveitando.")
        _emit_event(on_event, "configurado", reaproveitado=True)
        return
    parms = _montar_parametros_adicionais(cnpj_estabelecimento, SITEF_CNPJ_AUTOMACAO)
    resultado = _mk_buf(8)
    logger.info("ParametrosAdicionais: %s", parms)

    try:
        lib.ConfiguraIntSiTefInterativoExA(
            resultado,
            _b(_delim(SITEF_IP)),
            _b(SITEF_ID_LOJA.ljust(8)),
            _b(SITEF_ID_TERMINAL.ljust(8)),
            _b("000000"),
            _b(parms),
        )
        ret = _ascii_resultado(resultado)
        logger.info("ConfiguraIntSiTefInterativoExA → %d (%s)", ret, descrever_erro_configura(ret) if ret != 0 else "OK")
    except AttributeError:
        lib.ConfiguraIntSiTefInterativoA(
            resultado,
            _b(_delim(SITEF_IP)),
            _b(SITEF_ID_LOJA.ljust(8)),
            _b(SITEF_ID_TERMINAL.ljust(8)),
            _b(parms),
        )
        ret = _ascii_resultado(resultado)
        logger.info(
            "ConfiguraIntSiTefInterativoA (fallback) → %d (%s)",
            ret, descrever_erro_configura(ret) if ret != 0 else "OK",
        )

    if ret != 0:
        raise RuntimeError(formatar_codigo_configura(ret))

    _CNPJ_CONFIGURADO = cnpj_estabelecimento
    _emit_event(on_event, "configurado")


# TCs do comprovante TEF — via loja (122) tem prioridade no totem
_TC_CUPOM_LOJA = frozenset({122})
_TC_CUPOM_CLIENTE = frozenset({121})

# TCs que a função 130 devolve para CADA transação pendente (mapeamento
# confirmado em log real de pré-homologação: os valores de 211 batem com as
# funções usadas nos testes — 2=débito, 3=crédito, 122=PIX — e 1319 com os
# valores em centavos). Usados só para registrar evidência das pendências.
_TC_PEND_INDICE = 161
_TC_PEND_DATA = 163
_TC_PEND_HORA = 164
_TC_PEND_FUNCAO = 211
_TC_PEND_VALOR = 1319


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


def _resolver_cupons_brutos(
    cupom_loja: list,
    cupom_cliente: list,
    dados: dict,
    valor_reais: str = "",
) -> tuple[list, list]:
    """Como _resolver_cupom_bruto, mas devolve as DUAS vias separadas em vez de
    priorizar uma só — a Fiserv exige imprimir loja E cliente fisicamente.
    Usada apenas pelo fluxo principal de pagamento (_executar_loop /
    executar_transacao); as demais funções (cancelamento, funções
    administrativas) continuam usando _resolver_cupom_bruto sem alteração."""
    bloco_loja = list(cupom_loja) if cupom_loja else _extrair_cupom_bruto_de_dados(dados, (122,))
    bloco_cliente = list(cupom_cliente) if cupom_cliente else _extrair_cupom_bruto_de_dados(dados, (121,))
    if not bloco_loja and not bloco_cliente:
        # Nenhuma via veio explicitamente — fallback genérico não pertence a
        # nenhuma via específica, então vira só "loja" pra não duplicar texto.
        return _montar_cupom_fallback(dados, valor_reais), []
    return bloco_loja, bloco_cliente


def _cupom_bruto_texto(blocos: list) -> str:
    return "".join(blocos)


def _executar_loop(
    lib,
    funcao: int,
    on_event: EventCallback,
    valor_str: str = "0",
    num_parcelas: int = 1,
    restricao: str = "",
    coletar_registros: Optional[list] = None,
) -> tuple[int, dict, list, list]:
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
            bloco_loja, bloco_cliente = _resolver_cupons_brutos(cupom_loja, cupom_cliente, dados)
            logger.info(
                "Cupom bruto: loja=%d bloco(s)/%d chars, cliente=%d bloco(s)/%d chars",
                len(bloco_loja), len(_cupom_bruto_texto(bloco_loja)),
                len(bloco_cliente), len(_cupom_bruto_texto(bloco_cliente)),
            )
            if bool(bloco_loja) != bool(bloco_cliente):
                logger.warning(
                    "Cupom TEF: só a via %s veio da CliSiTef — a outra via não será impressa.",
                    "loja" if bloco_loja else "cliente",
                )
            return ret, dados, bloco_loja, bloco_cliente

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
            # Opt-in (só a resolução de pendências passa a lista): o TC do valor
            # fecha o registro de cada transação pendente — fotografa os campos
            # antes que o registro seguinte os sobrescreva em `dados`.
            if coletar_registros is not None and tc == _TC_PEND_VALOR and msg:
                coletar_registros.append({
                    "indice": dados.get(_TC_PEND_INDICE, "?"),
                    "data": dados.get(_TC_PEND_DATA, "?"),
                    "hora": dados.get(_TC_PEND_HORA, "?"),
                    "funcao": dados.get(_TC_PEND_FUNCAO, "?"),
                    "valor_centavos": msg,
                })
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
            # ANULA é um botão físico do pinpad — a CliSiTef manda essa
            # pergunta (tc==5013, "Operacao Cancelada?") esperando confirmação
            # de verdade, não uma resposta automática (Seq. 9). Outras
            # confirmações genéricas continuam automáticas como antes.
            pergunta = _norm(msg) if msg else ""
            if any(k in pergunta for k in ("cancelar", "cancela", "anular", "anula")):
                confirma = _aguardar_confirmacao_cancelamento(on_event, msg or "Cancelamento solicitado", tc)
                # Testado em hardware real: pra esse prompt específico
                # ("Operacao Cancelada?"), a CliSiTef usa "0" = confirma o
                # cancelamento e "1" = mantém a transação — invertido do
                # convencional sim=1/não=0.
                _responder(buffer, "0" if confirma else "1")
            else:
                _emit_event(on_event, "mensagem", texto=msg or "Confirmar?", destino="confirmacao")
                _responder(buffer, "0")

        elif c == 21:
            escolha = _selecionar_menu(msg, funcao, restricao)
            _emit_event(on_event, "menu", opcoes=msg, selecionado=escolha)
            _responder(buffer, escolha)

        elif c == 22:
            # Pode carregar uma mensagem real (ex.: "Sem comprovante",
            # "Transacao invalida") — não descartar silenciosamente.
            if msg:
                _emit_event(on_event, "mensagem", texto=msg, destino="operador", tipo_campo=tc)
            _responder(buffer, "")

        elif c == 23:
            # Se o SiTef pedir número de parcelas e já tivermos o valor, responde automaticamente
            if num_parcelas > 1 and tc in (7, 8, 9, 14, 800):
                _responder(buffer, str(num_parcelas))
                _emit_event(on_event, "mensagem", texto=f"Parcelas: {num_parcelas}", destino="operador", tipo_campo=tc)
            else:
                _zerar(buffer)

        elif c == 30 and tc == 505:
            # "Forneça o número de parcelas" — pergunta separada da escolha do
            # menu (c==21), vem depois dela nas modalidades parceladas.
            if num_parcelas > 1:
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
        _b(_delim(cupom)),
        _b(data),
        _b(hora),
        _b(_delim(SITEF_OPERADOR)),
        _b(restricao),
    )
    ret_inicia = _ascii_resultado(resultado2)
    logger.info("IniciaFuncao → %d (restricao=%r, parcelas=%d)", ret_inicia, restricao, num_parcelas)
    _emit_event(on_event, "iniciada", funcao=funcao, valor=valor_display, cupom=cupom)

    if ret_inicia != 10000:
        raise RuntimeError(formatar_codigo_geral(ret_inicia))

    ret_loop, dados, cupom_loja, cupom_cliente = _executar_loop(lib, funcao, on_event, valor_str, num_parcelas, restricao)
    if not cupom_loja and not cupom_cliente:
        cupom_loja, cupom_cliente = _resolver_cupons_brutos([], [], dados, valor_display)
    cupom_bruto_loja = _cupom_bruto_texto(cupom_loja)
    cupom_bruto_cliente = _cupom_bruto_texto(cupom_cliente)
    logger.info(
        "Loop finalizado: ret=%d (%s) aprovada=%s — loja: %d bloco(s)/%d chars, cliente: %d bloco(s)/%d chars",
        ret_loop, descrever_erro_geral(ret_loop) if ret_loop != 0 else "Aprovada",
        ret_loop == 0, len(cupom_loja), len(cupom_bruto_loja), len(cupom_cliente), len(cupom_bruto_cliente),
    )

    resultado = {
        "aprovada": ret_loop == 0,
        "resultado": ret_loop,
        "mensagem_resultado": "Aprovada" if ret_loop == 0 else formatar_codigo_geral(ret_loop),
        "cupom": cupom,
        # Necessários para confirmar/desfazer depois: FinalizaFuncaoSiTefInterativoA
        # identifica a transação por (NumeroCupom, DataFiscal, HoraFiscal).
        "data_fiscal": data,
        "hora_fiscal": hora,
        "nsu_sitef": dados.get(133, ""),
        "nsu_host": dados.get(134, ""),
        "autorizacao": dados.get(135, ""),
        # PIX não manda TC 135 (não tem "autorização" no sentido de cartão) —
        # TC 4077 é o número de documento da transação PIX, o mesmo que
        # aparece como "DOCUMENTO = ..." no texto do cupom.
        "documento_pix": dados.get(4077, ""),
        "modalidade": dados.get(101, ""),
        "bandeira": dados.get(156, ""),
        "dados": {str(k): v for k, v in dados.items()},
        # Via loja mantém as chaves antigas (compatibilidade com quem já lê
        # linhas_cupom/cupom_bruto); via cliente vai em chaves novas.
        "linhas_cupom": cupom_loja,
        "cupom_bruto": cupom_bruto_loja,
        "linhas_cupom_cliente": cupom_cliente,
        "cupom_bruto_cliente": cupom_bruto_cliente,
        "pix": funcao == 122,
    }

    sys.stdout.write(json.dumps(resultado, ensure_ascii=False) + "\n")
    sys.stdout.flush()

    # Se negada: finaliza imediatamente com confirma=0 (nada a confirmar)
    # Se aprovada: deixa pendente — o backend chamará FinalizaFuncaoSiTefInterativoA
    # somente APÓS impressão do cupom TEF e emissão do XML fiscal (Item 8.1.1 CliSiTef AA)
    resultado["pendente_confirmacao"] = ret_loop == 0
    if ret_loop != 0:
        ret_fin = _finalizar_funcao(lib, 0, cupom, data, hora)
        logger.info("Finaliza (transação negada, confirma=0) → %d", ret_fin)
        resultado["pendente_confirmacao"] = False

    _emit_event(
        on_event,
        "finalizada",
        aprovada=resultado["aprovada"],
        resultado=ret_loop,
        mensagem=dados.get(-1, "") or dados.get(0, ""),
    )
    return resultado


def confirmar_transacao(
    confirma: int,
    cupom: str,
    data: str,
    hora: str,
    cnpj_estabelecimento: str = "",
    on_event: EventCallback = None,
) -> int:
    """
    Finaliza a transação SiTef após impressão do cupom TEF e emissão do XML fiscal.
    Deve ser chamada pelo backend somente após esses dois passos (Item 8.1.1).
    confirma=1 → confirma (pagamento OK, comprovante impresso)
    confirma=0 → desfaz (falha na impressão ou no XML)

    cupom/data/hora identificam a transação a confirmar — precisam ser os
    mesmos valores usados no IniciaFuncaoSiTefInterativoA dela (vêm de
    executar_transacao: cupom/data_fiscal/hora_fiscal).
    """
    lib = carregar_lib()
    configurar(lib, cnpj_estabelecimento, on_event)
    ret_fin = _finalizar_funcao(lib, confirma, cupom, data, hora)
    logger.info(
        "Finaliza (confirma=%d, cupom=%s) → %d%s",
        confirma, cupom, ret_fin, "" if ret_fin == 0 else f" ({descrever_erro_geral(ret_fin)})",
    )
    _emit_event(on_event, "confirmacao_enviada", confirma=confirma, resultado=ret_fin)
    return ret_fin


def cancelar_transacao(
    valor_centavos: int,
    cupom_original: str,
    data_original: str,
    nsu_host: str,
    cnpj_estabelecimento: str = "",
    on_event: EventCallback = None,
    senha_supervisor: Optional[str] = None,
) -> dict:
    """
    Cancelamento via função SiTef 200 (Menu de Cancelamento — mesma acessada
    pela opção 3 do menu administrativo modalidade 110, "Cancelamento de
    transação"). Cobre cartão (débito/crédito); a função 123 é especificamente
    "Carteira Digital — Cancelamento" (PIX/QR), não cartão.
    data_original: AAAAMMDD da transação original.
    nsu_host: NSU do host retornado na transação original.
    senha_supervisor: senha digitada ao vivo pelo supervisor no painel admin
    (requisito Fiserv — TC 500 não pode ser respondido com valor pré-configurado
    silenciosamente). Se None, cai no fallback SITEF_SUPERVISOR_SENHA — reservado
    a fluxos totalmente automáticos sem humano (ex.: resolver_pendencias no boot).
    """
    lib = carregar_lib()
    configurar(lib, cnpj_estabelecimento, on_event)

    data = datetime.now().strftime("%Y%m%d")
    hora = datetime.now().strftime("%H%M%S")
    cupom_cancelamento = gerar_cupom_fiscal()

    valor_display = f"{valor_centavos // 100},{valor_centavos % 100:02d}"
    valor_str = f"{{{valor_display}}}"

    logger.info(
        "cancelar_transacao: funcao=200 valor=%s cupom_orig=%s data_orig=%s nsu_host=%s",
        valor_str, cupom_original, data_original, nsu_host,
    )

    resultado2 = _mk_buf(8)
    lib.IniciaFuncaoSiTefInterativoA(
        resultado2,
        _b("000200"),
        _b(valor_str),
        _b(_delim(cupom_cancelamento)),
        _b(data),
        _b(hora),
        _b(_delim(SITEF_OPERADOR)),
        _b(""),
    )
    ret_inicia = _ascii_resultado(resultado2)
    logger.info(
        "IniciaFuncao cancelamento → %d (%s)",
        ret_inicia, descrever_erro_geral(ret_inicia) if ret_inicia != 10000 else "OK",
    )

    if ret_inicia != 10000:
        raise RuntimeError(formatar_codigo_geral(ret_inicia))

    _emit_event(on_event, "iniciada", funcao=200, valor=valor_display, cupom=cupom_cancelamento)

    # Loop que responde automaticamente aos campos de cancelamento
    ret_loop, dados, linhas_cupom = _executar_loop_cancelamento(
        lib, on_event,
        valor_str=valor_str,
        nsu_host=nsu_host,
        data_original=data_original,
        senha_supervisor=senha_supervisor,
    )

    if not linhas_cupom:
        linhas_cupom = _resolver_cupom_bruto([], [], dados, valor_display)
    cupom_bruto = _cupom_bruto_texto(linhas_cupom)

    resultado = {
        "aprovada": ret_loop == 0,
        "resultado": ret_loop,
        "mensagem_resultado": "Aprovada" if ret_loop == 0 else formatar_codigo_geral(ret_loop),
        "nsu_sitef": dados.get(133, ""),
        "nsu_host": dados.get(134, ""),
        "cupom_bruto": cupom_bruto,
        "linhas_cupom": linhas_cupom,
    }

    confirma = 1 if ret_loop == 0 else 0
    ret_fin = _finalizar_funcao(lib, confirma, cupom_cancelamento, data, hora)
    logger.info("Finaliza (cancelamento, confirma=%d) → %d", confirma, ret_fin)

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
    senha_supervisor: Optional[str] = None,
) -> tuple[int, dict, list]:
    """
    Loop igual ao principal, mas responde automaticamente a:
    - c==34 (valor monetário) → valor_str
    - c==23/c==30 com tc de documento/NSU → nsu_host
    - c==23/c==30 com tc de data → data_original (ou DDMMAAAA, conforme o tc)
    """
    buf_resultado = _mk_buf(8)
    buf_cmd = _mk_buf(14)
    buf_tc = _mk_buf(14)
    buf_min = _mk_buf(8)
    buf_max = _mk_buf(8)
    continua = ctypes.create_string_buffer(b"000000", 8)
    buffer = ctypes.create_string_buffer(BUFFER_SIZE)
    buf_tam = ctypes.create_string_buffer(_b(str(BUFFER_SIZE).rjust(6, "0")), 8)

    # TCs conhecidos para documento/NSU no cancelamento.
    # 516 = "Numero do documento a ser cancelado" (visto na função 200, c==30).
    _TC_DOCUMENTO = frozenset({13, 14, 15, 23, 133, 134, 516})
    # TCs conhecidos para data no cancelamento (formato AAAAMMDD)
    _TC_DATA = frozenset({12, 17, 19, 45})
    # tc==515 ("Data da transacao") é pedido em DDMMAAAA, formato diferente
    # dos demais TCs de data — visto na função 200 (Menu de Cancelamento).
    _TC_DATA_DDMMAAAA = frozenset({515})

    data_original_ddmmaaaa = (
        data_original[6:8] + data_original[4:6] + data_original[0:4]
        if len(data_original or "") == 8 else data_original
    )

    dados: dict = {}
    cupom_cliente: list = []
    cupom_loja: list = []

    # Protege só contra o caso já visto de verdade: um campo de dado CONHECIDO
    # (documento/NSU ou data) sendo respondido com valor real e mesmo assim
    # repetido — sinal de que o formato está errado e nunca vai ser aceito.
    # NÃO se aplica a mensagens/estados genéricos (ex.: aguardando cartão no
    # pinpad), que legitimamente podem repetir várias vezes até o cliente agir
    # — igual já acontece sem problema no fluxo normal de venda.
    _repeticoes_campo: dict = {}

    def _repetiu_demais(chave: tuple, limite: int = 8) -> bool:
        _repeticoes_campo[chave] = _repeticoes_campo.get(chave, 0) + 1
        return _repeticoes_campo[chave] >= limite

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
            # Requisito Fiserv: TC 500 deve ser respondido com senha digitada ao
            # vivo pelo supervisor (via painel admin), não um valor fixo silencioso.
            # NUNCA logar o valor de `senha` aqui (nem debug, nem print).
            senha = senha_supervisor if senha_supervisor else SITEF_SUPERVISOR_SENHA
            _responder(buffer, senha)
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
                if _repetiu_demais(("doc", c, tc)):
                    raise RuntimeError(
                        f"Cancelamento travado: CliSiTef recusou repetidamente o NSU "
                        f"informado (c={c} tc={tc})."
                    )
                _responder(buffer, nsu_host)
            elif tc in _TC_DATA and data_original:
                if _repetiu_demais(("data", c, tc)):
                    raise RuntimeError(
                        f"Cancelamento travado: CliSiTef recusou repetidamente a data "
                        f"informada (c={c} tc={tc})."
                    )
                _responder(buffer, data_original)
            else:
                logger.warning(
                    "cancelamento: comando 23 (solicita dado) tc=%d nao mapeado — msg=%r",
                    tc, msg[:200] if msg else "",
                )
                _zerar(buffer)

        elif c == 30:
            # "Solicita dado" — visto na função 200 pedindo a data original da
            # transação (tc=515, formato DDMMAAAA, diferente do c==23), e também
            # o código do supervisor (tc=500, "Forneca o codigo do supervisor")
            # — visto em teste real, diferente do c in (1,2,3) usado no fluxo
            # normal de venda. NUNCA logar o valor de `senha` aqui.
            if tc == 500:
                senha = senha_supervisor if senha_supervisor else SITEF_SUPERVISOR_SENHA
                _responder(buffer, senha)
                _emit_event(on_event, "mensagem", texto="[Autenticação de supervisor]", destino="operador", tipo_campo=500)
            elif tc in _TC_DATA_DDMMAAAA and data_original_ddmmaaaa:
                if _repetiu_demais(("data_ddmmaaaa", c, tc)):
                    raise RuntimeError(
                        f"Cancelamento travado: CliSiTef recusou repetidamente a data "
                        f"(DDMMAAAA) informada (c={c} tc={tc})."
                    )
                _responder(buffer, data_original_ddmmaaaa)
            elif tc in _TC_DOCUMENTO and nsu_host:
                if _repetiu_demais(("doc", c, tc)):
                    raise RuntimeError(
                        f"Cancelamento travado: CliSiTef recusou repetidamente o NSU "
                        f"informado (c={c} tc={tc})."
                    )
                _responder(buffer, nsu_host)
            elif tc in _TC_DATA and data_original:
                if _repetiu_demais(("data", c, tc)):
                    raise RuntimeError(
                        f"Cancelamento travado: CliSiTef recusou repetidamente a data "
                        f"informada (c={c} tc={tc})."
                    )
                _responder(buffer, data_original)
            else:
                logger.warning(
                    "cancelamento: comando 30 (solicita dado) tc=%d nao mapeado — msg=%r",
                    tc, msg[:200] if msg else "",
                )
                _zerar(buffer)

        elif c == 21:
            escolha = _selecionar_menu(msg, 200)
            _emit_event(on_event, "menu", opcoes=msg, selecionado=escolha)
            _responder(buffer, escolha)

        elif c == 20:
            _responder(buffer, "0")

        elif c == 22:
            # Pode carregar uma mensagem real (ex.: "Sem comprovante",
            # "Transacao invalida") — não descartar silenciosamente.
            if msg:
                _emit_event(on_event, "mensagem", texto=msg, destino="operador", tipo_campo=tc)
            _responder(buffer, "")

        elif c == 29:
            _responder(buffer, "1")

        elif c in (4, 11, 12, 13, 14, 15, 16, 50, 51, 52):
            buffer.value = b""

        else:
            # Função 200 (Menu de Cancelamento) é mais ampla que a 123 e pode pedir
            # passos que o loop de cancelamento direto não previa (ex.: seleção de
            # tipo de transação, dados extras de identificação da venda original).
            # Log específico para identificar na prática o que falta tratar.
            logger.warning(
                "cancelamento: comando NAO TRATADO c=%d tc=%d min=%s max=%s msg=%r",
                c, tc, _ascii_resultado(buf_min), _ascii_resultado(buf_max),
                msg[:200] if msg else "",
            )
            _responder(buffer, "")


def _parse_opcoes_menu(msg: str) -> list:
    """Converte a string de opções de menu do SiTef ("1:Opção A;2:Opção B;...")
    em uma lista estruturada para o painel admin renderizar botões numerados
    (Tabela 2 do roteiro de pré-homologação)."""
    opcoes: list = []
    for opcao in (msg or "").split(";"):
        opcao = opcao.strip()
        if not opcao:
            continue
        partes = opcao.split(":", 1)
        if len(partes) == 2:
            opcoes.append({"indice": partes[0].strip(), "label": partes[1].strip()})
        else:
            opcoes.append({"indice": opcao, "label": opcao})
    return opcoes


def _aguardar_resposta_operador(
    on_event: EventCallback,
    *,
    tipo: str,
    mensagem: str = "",
    tc: int = 0,
    opcoes: Optional[list] = None,
    minimo: Optional[int] = None,
    maximo: Optional[int] = None,
    timeout: float = 300.0,
) -> str:
    """Emite um evento 'prompt' descrevendo o que a CliSiTef está pedindo e
    bloqueia (via _ler_mensagem_stdin) até o operador responder pelo painel
    admin — mesmo canal de stdin não-bloqueante usado no cancelamento
    interativo. Não loga o valor da resposta (pode ser senha de supervisor)."""
    # "tipo_prompt" (não "tipo"): o evento "prompt" já carrega tipo="prompt"
    # (ver _emit_event); usar a mesma chave aqui sobrescreveria esse marcador
    # quando homologacao_session.py fizer `{"tipo": "prompt", **prompt}`.
    payload: dict = {"tipo_prompt": tipo, "mensagem": mensagem, "tc": tc}
    if opcoes is not None:
        payload["opcoes"] = opcoes
    if minimo is not None:
        payload["minimo"] = minimo
    if maximo is not None:
        payload["maximo"] = maximo
    _emit_event(on_event, "prompt", **payload)

    resposta = _ler_mensagem_stdin(timeout=timeout)
    if resposta and resposta.get("acao") == "responder_prompt":
        valor = str(resposta.get("valor", ""))
    else:
        logger.warning("Timeout/sem resposta do operador (tipo=%s tc=%d)", tipo, tc)
        valor = ""

    _emit_event(on_event, "prompt_resolvido")
    return valor


def _executar_loop_interativo(lib, on_event: EventCallback) -> tuple[int, dict, list]:
    """Mesmo protocolo de _executar_loop, mas para funções administrativas/de
    teste (Menu Administrativo 110 e, se necessário, outras via código livre)
    rodadas interativamente a partir do painel admin: em vez
    de responder automaticamente aos comandos que exigem decisão/dado do
    operador (10/30/34 dado, 20 confirmação, 21 menu, 41 campo mascarado, TC
    500 senha de supervisor), pausa e espera a resposta chegar via painel
    (_aguardar_resposta_operador), como exigido pelo Roteiro de
    Pré-Homologação Fiserv."""
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
            return ret, dados, linhas_cupom

        c = _ascii_resultado(buf_cmd)
        tc = _ascii_resultado(buf_tc)
        msg = _dec(buffer.raw)

        logger.debug("[admin] cmd=%d tc=%d msg=%r", c, tc, msg[:80] if msg else "")

        if c == 0:
            if msg:
                _registrar_dado(dados, tc, msg)
            if tc in _TC_CUPOM_CLIENTE:
                _append_cupom_bruto(cupom_cliente, msg)
            elif tc in _TC_CUPOM_LOJA:
                _append_cupom_bruto(cupom_loja, msg)
            if tc == 584 and msg:
                _emit_event(on_event, "qrcode", payload=msg, tipo_campo=584)
            continue

        elif (c in (1, 2, 3) and tc == 500) or (c == 30 and tc == 500):
            # Senha do supervisor — TC 500 pode chegar via c==1/2/3 OU c==30
            # dependendo da função (bug confirmado em hardware real).
            senha = _aguardar_resposta_operador(
                on_event, tipo="senha_supervisor", mensagem=msg or "Senha do supervisor", tc=tc,
            )
            _responder(buffer, senha)

        elif c in (1, 2, 3):
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
            resposta = _aguardar_resposta_operador(
                on_event, tipo="confirmacao", mensagem=msg or "Confirmar?", tc=tc,
            )
            _responder(buffer, resposta or "0")

        elif c == 21:
            opcoes = _parse_opcoes_menu(msg)
            escolha = _aguardar_resposta_operador(
                on_event, tipo="menu", mensagem=msg, tc=tc, opcoes=opcoes,
            )
            _responder(buffer, escolha)

        elif c == 22:
            # Pode carregar uma mensagem real (ex.: "Sem comprovante",
            # "Transacao invalida") — não descartar silenciosamente.
            if msg:
                _emit_event(on_event, "mensagem", texto=msg, destino="operador", tipo_campo=tc)
            _responder(buffer, "")

        elif c == 23:
            _zerar(buffer)

        elif c in (10, 30, 34):
            minimo = _ascii_resultado(buf_min)
            maximo = _ascii_resultado(buf_max)
            resposta = _aguardar_resposta_operador(
                on_event, tipo="dado", mensagem=msg or "Informe o valor", tc=tc,
                minimo=minimo, maximo=maximo,
            )
            _responder(buffer, resposta)

        elif c == 29:
            _responder(buffer, "1")

        elif c == 41:
            senha = _aguardar_resposta_operador(
                on_event, tipo="campo_mascarado", mensagem=msg or "Informe o dado", tc=tc,
            )
            _responder(buffer, senha)

        else:
            logger.debug("[admin] cmd=%d — resposta vazia", c)
            _responder(buffer, "")


def executar_funcao_administrativa(
    funcao_codigo: str,
    cnpj_estabelecimento: str = "",
    on_event: EventCallback = None,
) -> dict:
    """Roda uma função administrativa/de teste CliSiTef (Menu Administrativo
    110 e, se necessário, outras via código livre) de forma
    interativa a partir do painel admin, emitindo evento 'prompt' e esperando
    a resposta do operador a cada comando que exigir decisão/dado — ver
    _executar_loop_interativo. Ao final, emite evento 'finalizada'."""
    lib = carregar_lib()
    configurar(lib, cnpj_estabelecimento, on_event)

    data = datetime.now().strftime("%Y%m%d")
    hora = datetime.now().strftime("%H%M%S")
    cupom = gerar_cupom_fiscal()
    funcao_fmt = str(funcao_codigo).strip().rjust(6, "0")

    logger.info("IniciaFuncao administrativa funcao=%s cupom=%s", funcao_fmt, cupom)

    resultado_inicio = _mk_buf(8)
    lib.IniciaFuncaoSiTefInterativoA(
        resultado_inicio,
        _b(funcao_fmt),
        _b("{0,00}"),
        _b(_delim(cupom)),
        _b(data),
        _b(hora),
        _b(_delim(SITEF_OPERADOR)),
        _b(""),
    )
    ret_inicia = _ascii_resultado(resultado_inicio)
    if ret_inicia != 10000:
        raise RuntimeError(formatar_codigo_geral(ret_inicia))

    _emit_event(on_event, "iniciada", funcao=funcao_fmt, cupom=cupom)

    ret_loop, dados, linhas_cupom = _executar_loop_interativo(lib, on_event)
    cupom_bruto = _cupom_bruto_texto(linhas_cupom)

    # -2 ("Operação cancelada pelo operador") é o jeito NORMAL de uma função
    # administrativa/menu terminar quando o operador sai pela opção de saída —
    # não é uma falha, então não deve ser tratado como erro na função 110.
    _RET_NORMAL_FUNCAO_ADMIN = {0, -2}
    resultado = {
        "aprovada": ret_loop in _RET_NORMAL_FUNCAO_ADMIN,
        "resultado": ret_loop,
        "mensagem_resultado": "Aprovada" if ret_loop == 0 else formatar_codigo_geral(ret_loop),
        "funcao": funcao_fmt,
        "cupom": cupom,
        "dados": {str(k): v for k, v in dados.items()},
        "linhas_cupom": linhas_cupom,
        "cupom_bruto": cupom_bruto,
    }

    # FinalizaFuncaoSiTefInterativoA "se aplicável": algumas funções
    # administrativas não exigem/aceitam finalização explícita — melhor
    # esforço, não deve derrubar o resultado já obtido do loop.
    try:
        ret_fin = _finalizar_funcao(lib, 0, cupom, data, hora)
        logger.info("Finaliza (função %s, confirma=0) → %d", funcao_fmt, ret_fin)
    except Exception:
        logger.warning(
            "FinalizaFuncaoSiTefInterativoA (função %s) falhou/não aplicável",
            funcao_fmt, exc_info=True,
        )

    _emit_event(
        on_event, "finalizada",
        aprovada=resultado["aprovada"],
        resultado=ret_loop,
        mensagem_resultado=resultado["mensagem_resultado"],
        funcao=funcao_fmt,
    )
    return resultado


def _descrever_pendencia(reg: dict) -> str:
    """Uma linha legível por transação pendente, para evidência em log."""
    centavos = str(reg.get("valor_centavos", "")).strip()
    if centavos.isdigit():
        valor = f"R$ {int(centavos) // 100},{int(centavos) % 100:02d}"
    else:
        valor = "valor não informado"
    return (
        f"#{reg.get('indice', '?')} data={reg.get('data', '?')} hora={reg.get('hora', '?')} "
        f"funcao={reg.get('funcao', '?')} {valor}"
    )


def resolver_pendencias(cnpj_estabelecimento: str = "", on_event: EventCallback = None) -> int:
    """Resolve transações pendentes (função 130) na inicialização — SEMPRE
    estornando, nunca confirmando (ver comentário no final da função)."""
    lib = carregar_lib()
    configurar(lib, cnpj_estabelecimento, on_event)

    data = datetime.now().strftime("%Y%m%d")
    cupom = gerar_cupom_fiscal()

    resultado = _mk_buf(8)
    # Ordem confirmada por desassembly: arg2 = DataFiscal (cópia de 8 chars
    # fixos) e arg3 = NumeroCupom (delimitado, via ffae5) — o inverso do que
    # este código passava. Antes só "funcionava" por acidente: o cupom
    # AAAAMMDDHHMMSS truncado em 8 dava a data certa, e a data virava cupom "0".
    cupom_delim = _delim(cupom)
    buf_data = ctypes.create_string_buffer(_b(data), len(data) + 2)
    buf_cupom = ctypes.create_string_buffer(_b(cupom_delim), len(cupom_delim) + 2)
    lib.ObtemQuantidadeTransacoesPendentesA(resultado, buf_data, buf_cupom)
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
        _b(_delim(cupom)),
        _b(data),
        _b(hora),
        _b(_delim(SITEF_OPERADOR)),
        _b(""),
    )
    ret_inicia130 = _ascii_resultado(resultado2)
    if ret_inicia130 != 10000:
        logger.warning(
            "IniciaFuncao pendências (130) falhou: %d — %s",
            ret_inicia130, descrever_erro_geral(ret_inicia130),
        )
        return qty

    registros: list[dict] = []
    ret_loop, _, _, _ = _executar_loop(lib, 130, on_event, "0", coletar_registros=registros)
    logger.info(
        "Pendências: loop da função 130 terminou ret=%d (%s)",
        ret_loop, descrever_erro_geral(ret_loop) if ret_loop != 0 else "OK",
    )

    # Evidência (roteiro de pré-homologação): o que a CliSiTef reportou como
    # pendente. Cupom bruto vazio é normal aqui e NÃO impede o estorno — a
    # função 130 não devolve comprovante das pendências.
    if registros:
        for reg in registros:
            logger.info("Pendência pendente de estorno: %s", _descrever_pendencia(reg))
    else:
        logger.info(
            "Pendências: a CliSiTef não detalhou registros (qty=%d) — estorno segue igual.", qty,
        )

    # SEMPRE desfaz, nunca confirma. Uma transação que ficou pendente é, por
    # definição, uma transação sem prova de que o comprovante chegou ao cliente
    # (item 8.1.1 do CliSiTef AA só permite confirmar DEPOIS de imprimir).
    # Confirmar às cegas aqui cobraria o cliente sem cupom.
    logger.info(
        "Pendências: estornando %d transação(ões) — FinalizaFuncaoSiTefInterativoA(confirma=0)...",
        qty,
    )
    try:
        ret_fin = _finalizar_funcao(lib, 0, cupom, data, hora)  # 0 = desfazer
    except Exception:
        logger.error(
            "Pendências: FALHA ao estornar %d transação(ões) — exceção em "
            "FinalizaFuncaoSiTefInterativoA. As pendências continuam abertas no SiTef.",
            qty, exc_info=True,
        )
        raise

    if ret_fin == 0:
        logger.info("Pendências: %d transação(ões) ESTORNADA(S) COM SUCESSO (ret=0).", qty)
    else:
        logger.error(
            "Pendências: FALHA ao estornar — FinalizaFuncaoSiTefInterativoA devolveu %d (%s). "
            "As pendências podem continuar abertas no SiTef.",
            ret_fin, descrever_erro_geral(ret_fin),
        )
    return qty
