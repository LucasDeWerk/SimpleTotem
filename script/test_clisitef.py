#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CliSiTef Test Suite
Testa as principais funcionalidades da biblioteca CliSiTef
contra o SiTef Simulado.

Uso:
    cd "clisitef-7.0.117.112.r3-Simulado-Linux64"
    python3 ../test_clisitef.py
"""

import ctypes
import json
import os
import sys
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÕES — ajuste conforme seu ambiente
# ─────────────────────────────────────────────────────────────────────────────

IP_SITEF    = "192.168.10.12"
ID_LOJA     = "00000000"   # Código fixo do SiTef Demonstração/Simulado
ID_TERMINAL = "ST000001"   # Formato XXnnnnnn — nunca use 000900-000999
OPERADOR    = "01"

BUFFER_SIZE = 32768  # spec VRS-258 p.28: mínimo 20.000 bytes; folga extra

# Diretório das bibliotecas — mesmo diretório do script
LIB_DIR  = os.path.dirname(os.path.abspath(__file__))
LIB_PATH = os.path.join(LIB_DIR, "libclisitef.so")

# ─────────────────────────────────────────────────────────────────────────────
# TABELAS
# ─────────────────────────────────────────────────────────────────────────────

FUNCOES = {
    # (nome, codigo_funcao, pede_valor)
    "Menu de Pagamento (geral)"      : (0,   True),
    "Crédito"                        : (2,   True),
    "Débito"                         : (3,   True),
    "Voucher / Benefício"            : (4,   True),
    "Menu Administrativo"            : (110, False),
    "Menu de Cancelamento"           : (200, False),
    "Carteira Digital — Venda"       : (122, True),
    "Carteira Digital — Cancelamento": (123, False),
    "Carteira Digital — Saque"       : (124, False),
    "Carteira Digital — Recarga"     : (125, True),
    "Consulta Saldo Cart. Digital"   : (127, False),
}

ERROS_CONFIGURA = {
    1:  "Endereço IP inválido ou não resolvido",
    2:  "Código da loja inválido",
    3:  "Código de terminal inválido",
    6:  "Erro na inicialização do TCP/IP",
    7:  "Falta de memória",
    8:  "CliSiTef não encontrada ou com problemas",
    9:  "Configuração de servidores SiTef excedida",
    10: "Erro de acesso na pasta CliSiTef (verifique permissões)",
    11: "Dados inválidos passados pela automação",
    12: "Modo seguro não ativo (arquivo .cha ausente no servidor)",
    13: "Caminho DLL inválido (path das bibliotecas muito grande)",
}

ERROS_GERAIS = {
    -1:  "Módulo não inicializado — chame ConfiguraInt primeiro",
    -2:  "Operação cancelada pelo operador",
    -3:  "Função/modalidade inexistente ou inválida",
    -4:  "Falta de memória no PDV",
    -5:  "Sem comunicação com o SiTef",
    -6:  "Operação cancelada pelo usuário no pinpad",
    -8:  "CliSiTef desatualizada — função não implementada",
    -9:  "ContinuaFuncao chamada sem IniciaFuncao",
    -10: "Parâmetro obrigatório não passado",
    -12: "Loop anterior não terminou (retorno 10000 não atingido)",
    -13: "Documento fiscal não encontrado",
    -15: "Operação cancelada pela automação",
    -20: "Parâmetro inválido para a função",
    -21: "Palavra proibida usada em coleta aberta (ex: SENHA)",
    -25: "Erro no Correspondente Bancário — realizar sangria",
    -30: "Erro de acesso ao arquivo (verifique permissões leitura/escrita)",
    -40: "Transação negada pelo servidor SiTef",
    -41: "Dados inválidos",
    -43: "Problema na execução de rotina no pinpad",
    -50: "Transação não segura",
    -100:"Erro interno do módulo",
}

# Descrições de cada TipoCampo (TC) retornado com Comando=0 (armazenar valor)
# Fonte: Spec VRS-258 seções 5.3.2 e 5.3.3
TIPO_CAMPO = {
    # ── Campos de controle de fluxo ──────────────────────────────────────────
    -1:   "Sem informação para tratar",
    0:    "Coleta de dados concluída",
    1:    "Dados de confirmação (DadosConf;IndSiTef;EndSiTef)",
    2:    "Código de função SiTef",
    3:    "Tipo de parcelamento",
    4:    "Número de parcelas",

    # ── Modalidade / Comprovante ──────────────────────────────────────────────
    100:  "Modalidade de pagamento (xxnn: grupo+sub)",
    101:  "Texto da modalidade real de pagamento",
    102:  "Texto descritivo do comprovante",
    105:  "Data/hora da transação (AAAAMMDDHHMMSS)",
    121:  "1ª via do comprovante (via cliente)",
    122:  "2ª via do comprovante (via loja)",
    123:  "Tipo do comprovante",
    124:  "Texto adicional do comprovante",
    125:  "Texto do cabeçalho do comprovante",

    # ── Identificadores da transação ─────────────────────────────────────────
    130:  "Referência da transação",
    131:  "Índice da instituição",
    132:  "Índice do tipo de cartão",
    133:  "NSU SiTef (6 dígitos)",
    134:  "NSU Host (até 20 dígitos)",
    135:  "Código de autorização de crédito (até 15 chars)",
    136:  "BIN do cartão (primeiros 6 dígitos)",
    137:  "Número do terminal na rede autorizadora",
    138:  "Data da transação no host (AAMMDD)",
    139:  "Hora da transação no host (HHMMSS)",
    140:  "Código de resposta do host",
    141:  "Valor da transação aprovado pelo host (centavos)",
    142:  "Código único da transação (CTR)",

    # ── Estabelecimento / Rede ────────────────────────────────────────────────
    156:  "Nome da instituição / bandeira",
    157:  "Código do estabelecimento",
    158:  "Código da rede autorizadora",
    159:  "Nome da rede autorizadora",

    # ── Dados do cartão ───────────────────────────────────────────────────────
    500:  "Número do cartão (mascarado)",
    501:  "Nome do portador impresso no cartão",
    502:  "Data de validade do cartão (MMAA ou AAAAMM)",
    503:  "Trilha 2 do cartão (mascarada)",
    504:  "Número de sequência do cartão",
    505:  "Código de serviço do cartão",

    # ── Cheque ────────────────────────────────────────────────────────────────
    600:  "Banco do cheque",
    601:  "Agência do cheque",
    602:  "Conta do cheque",
    603:  "Número do cheque",
    604:  "Valor do cheque (centavos)",
    605:  "COMPE do banco do cheque",

    # ── Campos estendidos e específicos ──────────────────────────────────────
    1000: "CPF/CNPJ do portador",
    1001: "Endereço de e-mail do portador",
    1002: "Data de validade do cartão (campo estendido)",
    1003: "Nome do portador do cartão",
    1004: "Código do produto (crédito parcelado etc.)",
    1005: "Número de parcelas (campo estendido)",
    1006: "Valor da parcela (centavos)",
    1007: "Valor da entrada (centavos)",
    1008: "Valor total financiado (centavos)",
    1009: "Taxa de juros ao mês (%)",
    1010: "CET — Custo Efetivo Total",
    1011: "Número do documento gerado",
    1012: "Código de barras do documento",
    1013: "Linha digitável do documento",

    # ── Tipo de leitura / pinpad ──────────────────────────────────────────────
    2090: "Tipo de leitura do cartão (0=tarja,1=chip,2=sem contato,3=digitado)",
    2091: "Resultado da leitura do chip (EMV)",
    2092: "Dados EMV da transação (TLV hex)",
    2093: "Criptograma EMV (ARQC/TC/AAC)",
    2094: "AID do aplicativo EMV",
    2095: "Nome do aplicativo EMV",
    2096: "TVR — Terminal Verification Results",
    2097: "TSI — Transaction Status Information",
    2098: "IAD — Issuer Application Data",
    2099: "Código do país do cartão (ISO 3166)",

    # ── Erros / diagnóstico ───────────────────────────────────────────────────
    4100: "Diagnóstico de erro de comunicação",
    4200: "Mensagem de diagnóstico interno",
    4221: "Indicador de cartão pré-pago (0/1)",

    # ── Eventos / estados do loop (seção 5.3.3) ──────────────────────────────
    5000: "Evento: início da comunicação com o host",
    5001: "Evento: comunicação com host concluída",
    5002: "Evento: aguardando ação no pinpad",
    5003: "Evento: leitura do cartão iniciada",
    5004: "Evento: leitura do cartão concluída",
    5005: "Evento: digitação de senha iniciada",
    5006: "Evento: digitação de senha concluída",
    5007: "Evento: processamento EMV iniciado",
    5008: "Evento: processamento EMV concluído",
    5100: "Evento: impressão do comprovante iniciada",
    5101: "Evento: impressão do comprovante concluída",
    5200: "Evento: operação cancelada pelo operador",
    5201: "Evento: operação cancelada pelo portador no pinpad",
    5300: "Evento: timeout de comunicação com o host",
    5301: "Evento: timeout de operação no pinpad",
    5400: "Evento: saldo disponível no cartão",
    5401: "Evento: limite de crédito disponível",
    5500: "Evento: QRCode gerado — aguardando leitura",
    5501: "Evento: QRCode lido com sucesso",
}

# Comandos retornados por ContinuaFuncaoSiTefInterativo
# Fonte: Spec VRS-258 seção 5.3.1
COMANDOS = {
    0:  "Armazenar valor",                          # lib retorna dado para a automação guardar
    1:  "Mensagem ao operador",
    2:  "Mensagem ao cliente",
    3:  "Mensagem ao operador e cliente",
    4:  "Título do menu",
    10: "Coletar dado alfanumérico",
    11: "Limpar visor do operador",
    12: "Limpar visor do cliente",
    13: "Limpar ambos visores",
    14: "Limpar título do menu",
    16: "Remover cabeçalho",
    20: "Confirmar SIM/NÃO",                        # retornar '0'=sim '1'=não no Buffer
    21: "Selecionar opção de menu",                 # Buffer contém "1:txt;2:txt;..." → retornar índice
    22: "Aguardar tecla do operador",
    23: "Verificar interrupção de periférico",      # NÃO inserir delay!
    29: "Coletar campo silencioso (forma pagto)",   # passar direto, sem exibir ao operador
    30: "Coletar campo",
    31: "Coletar cheque",
    34: "Coletar valor monetário",
    35: "Coletar código de barras",
    41: "Coletar campo mascarado",
    52: "Exibir mensagem (QRCode / aguardo)",
}

# ─────────────────────────────────────────────────────────────────────────────
# UTILITÁRIOS
# ─────────────────────────────────────────────────────────────────────────────

def b(s: str) -> bytes:
    """Codifica string para bytes latin-1 (padrão CliSiTef)."""
    return s.encode("latin-1")


def dec(raw: bytes) -> str:
    """Decodifica bytes vindo da CliSiTef, removendo delimitadores {}."""
    s = raw.decode("latin-1", errors="replace").rstrip("\x00").strip()
    # Protocolo CliSiTef envolve valores em {} — removemos para exibição
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1]
    return s


def now_date() -> str:
    return datetime.now().strftime("%Y%m%d")   # AAAAMMDD


def now_time() -> str:
    return datetime.now().strftime("%H%M%S")   # HHMMSS


_cupom_counter = int(datetime.now().strftime("%H%M%S"))

def proximo_cupom() -> str:
    """Retorna um número de cupom sempre crescente (max 20 chars)."""
    global _cupom_counter
    _cupom_counter += 1
    return str(_cupom_counter)


def sep(c="─", n=62):
    print(c * n)


def status(ret: int, label: str = "Retorno"):
    if ret == 0:
        icone = "✅"
    elif ret == 10000:
        icone = "🔄"
    else:
        icone = "❌"
    desc = ERROS_GERAIS.get(ret, "")
    print(f"  {icone} {label}: {ret}  {('— ' + desc) if desc else ''}")


# ─────────────────────────────────────────────────────────────────────────────
# CARREGAR BIBLIOTECA
# ─────────────────────────────────────────────────────────────────────────────

def carregar_lib() -> ctypes.CDLL:
    if not os.path.exists(LIB_PATH):
        print(f"  ❌ Biblioteca não encontrada: {LIB_PATH}")
        print(f"     Verifique se LIB_DIR está correto no topo do script.")
        sys.exit(1)

    # A CliSiTef procura o CliSiTef.ini no diretório de trabalho atual.
    # Garantimos que o CWD seja o diretório das bibliotecas.
    os.chdir(LIB_DIR)
    print(f"  📂 Diretório de trabalho: {LIB_DIR}")

    # Pré-carrega dependências com RTLD_GLOBAL para que libclisitef.so as encontre
    for dep in ["libcurl64.so", "libemv64.so", "libqrencode64.so"]:
        dep_path = os.path.join(LIB_DIR, dep)
        if os.path.exists(dep_path):
            ctypes.CDLL(dep_path, mode=ctypes.RTLD_GLOBAL)

    lib = ctypes.CDLL(LIB_PATH)

    # ── Usamos a interface ASCII (sufixo A) — mais segura para Python ────────
    # Todos os parâmetros são strings, retorno via buffer de saída fixo 6 bytes.

    # ConfiguraIntSiTefInterativoA(Resultado, IPSiTef, IdLoja, IdTerminal, Reservado)
    lib.ConfiguraIntSiTefInterativoA.restype  = None
    lib.ConfiguraIntSiTefInterativoA.argtypes = [
        ctypes.POINTER(ctypes.c_char),   # Resultado  (saída, fixo 6)
        ctypes.c_char_p,   # IPSiTef
        ctypes.c_char_p,   # IdLoja     (fixo 8)
        ctypes.c_char_p,   # IdTerminal (fixo 8)
        ctypes.c_char_p,   # Reservado  (fixo 6, passar "000000")
    ]

    # IniciaFuncaoSiTefInterativoA(Resultado, Funcao, Valor, CupomFiscal,
    #                               DataFiscal, HoraFiscal, Operador, ParamAdic)
    lib.IniciaFuncaoSiTefInterativoA.restype  = None
    lib.IniciaFuncaoSiTefInterativoA.argtypes = [
        ctypes.POINTER(ctypes.c_char),   # Resultado  (saída, fixo 6)
        ctypes.c_char_p,   # Funcao     (fixo 6)
        ctypes.c_char_p,   # Valor
        ctypes.c_char_p,   # CupomFiscal
        ctypes.c_char_p,   # DataFiscal
        ctypes.c_char_p,   # HoraFiscal
        ctypes.c_char_p,   # Operador
        ctypes.c_char_p,   # ParamAdic
    ]

    # ContinuaFuncaoSiTefInterativoA(Resultado, Comando, TipoCampo,
    #                                 TamanhoMinimo, TamanhoMaximo,
    #                                 Buffer, TamBuffer, Continua)
    #
    # IMPORTANTE: Usamos POINTER(c_char) ao invés de c_char_p para buffers
    # mutáveis. c_char_p pode extrair .value (até o 1º \x00) e criar um
    # ponteiro temporário, fazendo a biblioteca receber um buffer de 2 bytes
    # ao invés de 32768 → causa erro -4.
    _pchar = ctypes.POINTER(ctypes.c_char)
    lib.ContinuaFuncaoSiTefInterativoA.restype  = None
    lib.ContinuaFuncaoSiTefInterativoA.argtypes = [
        _pchar,            # Resultado     (saída, fixo 6)
        _pchar,            # Comando       (saída, fixo 12)
        _pchar,            # TipoCampo     (saída, fixo 12)
        _pchar,            # TamanhoMinimo (saída, fixo 6)
        _pchar,            # TamanhoMaximo (saída, fixo 6)
        _pchar,            # Buffer        (entrada/saída, BUFFER_SIZE)
        _pchar,            # TamBuffer     (fixo 6)
        _pchar,            # Continua      (fixo 6, "000000"=prosseguir)
    ]

    # FinalizaFuncaoSiTefInterativoA(Resultado, Confirma)
    lib.FinalizaFuncaoSiTefInterativoA.restype  = None
    lib.FinalizaFuncaoSiTefInterativoA.argtypes = [
        ctypes.POINTER(ctypes.c_char),   # Resultado (saída, fixo 6)
        ctypes.POINTER(ctypes.c_char),   # Confirma  (fixo 6, "000001" ou "000000")
    ]

    # ObtemQuantidadeTransacoesPendentes — interface ASCII
    lib.ObtemQuantidadeTransacoesPendentesA.restype  = None
    lib.ObtemQuantidadeTransacoesPendentesA.argtypes = [
        ctypes.POINTER(ctypes.c_char),   # Resultado    (saída, fixo 6)
        ctypes.POINTER(ctypes.c_char),   # CupomFiscal
        ctypes.POINTER(ctypes.c_char),   # DataFiscal
    ]

    return lib


# ─────────────────────────────────────────────────────────────────────────────
# FASE 1 — CONFIGURAR
# ─────────────────────────────────────────────────────────────────────────────

def ascii_resultado(buf: ctypes.Array) -> int:
    """Converte buffer de resultado ASCII (fixo 6) para int."""
    try:
        return int(dec(buf.raw).strip() or "0")
    except ValueError:
        return -999


def mk_buf(size: int = 8) -> ctypes.Array:
    """Cria buffer mutável zerado."""
    return ctypes.create_string_buffer(size)


def zerar_buffer(buf: ctypes.Array) -> None:
    """Zera completamente um buffer ctypes."""
    # Preenche com zeros usando memmove (a forma segura)
    ctypes.memmove(ctypes.addressof(buf), b"\x00" * len(buf), len(buf))


def responder(buf: ctypes.Array, valor: str) -> None:
    """Zera o buffer e escreve a resposta envolvida em {} (protocolo CliSiTef)."""
    zerar_buffer(buf)
    if valor:
        buf.value = f"{{{valor}}}".encode("latin-1")
    # Se valor vazio, buffer fica zerado


def configurar(lib) -> bool:
    sep("═")
    print("  CONFIGURANDO CLISITEF")
    sep("═")
    print(f"  IP SiTef    : {IP_SITEF}")
    print(f"  ID Loja     : {ID_LOJA}")
    print(f"  ID Terminal : {ID_TERMINAL}")
    sep()

    resultado = mk_buf(8)

    lib.ConfiguraIntSiTefInterativoA(
        resultado,
        b(IP_SITEF),
        b(ID_LOJA.ljust(8)),
        b(ID_TERMINAL.ljust(8)),
        b("000000"),          # Reservado
    )

    ret = ascii_resultado(resultado)
    status(ret, "ConfiguraIntSiTefInterativoA")

    if ret != 0:
        desc = ERROS_CONFIGURA.get(ret, "Erro desconhecido")
        print(f"  ⚠️  {desc}")
        return False

    print("  ✅ Configuração OK\n")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# FASE 2+3 — LOOP DE TRANSAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

def executar_loop(lib, dados_transacao: dict) -> tuple:
    """
    Executa o loop ContinuaFuncaoSiTefInterativoA até o fim.
    Retorna (ret_final: int, houve_cupom: bool, linhas_cupom: list[str])
    Preenche dados_transacao: dict[tc: int -> valor: str] com todos os campos TC=0.

    Buffers: Resultado/TamMinimo/TamMaximo/PosCursor = Fixo 6 (spec VRS-258 p.28)
             Comando e TipoCampo = Fixo 12 (spec VRS-258 p.28) — bug comum usar 8!
    """
    resultado  = mk_buf(8)
    buf_cmd    = mk_buf(14)  # Fixo 12 na interface ASCII (spec p.28)
    buf_tc     = mk_buf(14)  # Fixo 12 na interface ASCII (spec p.28)
    buf_min    = mk_buf(8)
    buf_max    = mk_buf(8)
    continua   = ctypes.create_string_buffer(b"000000", 8)  # Continua=0: prosseguir (spec p.29)
    buffer     = ctypes.create_string_buffer(BUFFER_SIZE)
    buf_tam    = ctypes.create_string_buffer(b(str(BUFFER_SIZE).rjust(6, "0")), 8)  # TamBuffer fixo 6

    houve_cupom  = False
    linhas_cupom = []
    _msgs_exibidas = set()   # evita repetir a mesma mensagem no terminal
    _aguardando_pinpad = False

    sep()
    print("  LOOP DE TRANSAÇÃO")
    sep()

    while True:
        # Reseta buffers de saída antes de cada chamada
        continua.value = b"000000"
        buf_tam.value = b(str(BUFFER_SIZE).rjust(6, "0"))

        lib.ContinuaFuncaoSiTefInterativoA(
            resultado,
            buf_cmd,
            buf_tc,
            buf_min,
            buf_max,
            buffer,
            buf_tam,
            continua,
        )

        ret = ascii_resultado(resultado)

        # DEBUG — remova quando estiver estável
        print(f"  [DBG] ret={ret!r} cmd={buf_cmd.raw!r} tc={buf_tc.raw!r} "
              f"min={buf_min.raw!r} max={buf_max.raw!r} cont={continua.raw!r} "
              f"buf={dec(buffer.raw)[:60]!r}")

        if ret != 10000:
            return ret, houve_cupom, linhas_cupom

        c  = ascii_resultado(buf_cmd)
        tc = ascii_resultado(buf_tc)
        mn = ascii_resultado(buf_min)
        mx = ascii_resultado(buf_max)
        msg = dec(buffer.raw)
        desc_cmd = COMANDOS.get(c, f"Cmd:{c}")

        # ── Armazenar todos os campos TC=0 em dados_transacao ───────────────
        if c == 0 and msg:
            dados_transacao[tc] = msg

        # ── Cupom TEF — TipoCampo 121/122 são vias do comprovante ────────────
        if c == 0 and tc in (121, 122, 1, 2, 3, 4) and msg:
            houve_cupom = True
            linhas_cupom.append(msg)
            print(f"  🧾 [CUPOM TC:{tc}] {msg}")
            buffer.value = b""
            continue

        # ── Armazenar valor retornado pela lib (c=0) ou exibir mensagem ─────
        if c in (0, 1, 2, 3, 52):
            if msg and msg not in _msgs_exibidas:
                icone = "👤" if c in (2, 3) else "🖥️ "
                print(f"  {icone} [{desc_cmd} | TC:{tc}] {msg}")
                _msgs_exibidas.add(msg)
                _aguardando_pinpad = False
            elif not msg and not _aguardando_pinpad:
                print("  ⌛ Aguardando ação no pinpad...")
                _aguardando_pinpad = True
            # NOTE: For c=0 (store value), per spec p.30, we should NOT modify the buffer.
            # The library wrote data there and we must leave it unchanged.
            if c != 0:
                buffer.value = b""

        # ── Limpar visores / título / cabeçalho ──────────────────────────────
        elif c in (4, 11, 12, 13, 14, 15, 16):
            buffer.value = b""

        # ── Confirmar SIM/NÃO ────────────────────────────────────────────────
        # retorno: '0' = confirma, '1' = cancela
        elif c == 20:
            print(f"\n  ❓ [{desc_cmd} | TC:{tc}]")
            if msg:
                print(f"     {msg}")
            resp = input("     >> S/N: ").strip().upper()
            responder(buffer, "1" if resp == "N" else "0")

        # ── Menu de seleção ──────────────────────────────────────────────────
        # Buffer contém "1:texto;2:texto;..." → retornar índice escolhido
        elif c == 21:
            _msgs_exibidas.clear()
            _aguardando_pinpad = False
            print(f"\n  📋 [{desc_cmd} | TC:{tc}]")
            if msg:
                for item in msg.split(";"):
                    if item.strip():
                        print(f"     {item.strip()}")
            escolha = input("     >> Opção: ").strip()
            responder(buffer, escolha)

        # ── Aguardar tecla do operador ────────────────────────────────────────
        elif c == 22:
            if msg:
                print(f"  ⌛ {msg}")
            input("     >> [Enter para continuar]: ")
            responder(buffer, "")

        # ── Interrupção de periférico — NÃO inserir delay! ───────────────────
        elif c == 23:
            zerar_buffer(buffer)  # sem resposta, apenas continuar

        # ── Campo silencioso (formas de pagamento, etc.) ──────────────────────
        elif c == 29:
            _msgs_exibidas.clear()
            _aguardando_pinpad = False
            print(f"\n  🔇 [{desc_cmd} | TC:{tc}]  min:{mn}  max:{mx}  opções:{msg}")
            entrada = input("     >> Valor (ex: 1=À Vista): ").strip()
            responder(buffer, entrada)

        # ── Coletar dado alfanumérico / numérico ─────────────────────────────
        elif c in (10, 30):
            print(f"\n  📥 [{desc_cmd} | TC:{tc}]  min:{mn}  max:{mx}")
            if msg:
                print(f"     {msg}")
            entrada = input("     >> ").strip()
            responder(buffer, entrada)

        # ── Coletar valor monetário ──────────────────────────────────────────
        elif c == 34:
            print(f"\n  💰 [{desc_cmd} | TC:{tc}]  min:{mn}  max:{mx}")
            if msg:
                print(f"     {msg}")
            val = input("     >> Valor (ex: 10,00): ").strip()
            responder(buffer, val)

        # ── Coletar código de barras ─────────────────────────────────────────
        elif c == 35:
            print(f"\n  📷 [{desc_cmd} | TC:{tc}]")
            if msg:
                print(f"     {msg}")
            cod = input("     >> Código de barras: ").strip()
            responder(buffer, cod)

        # ── Coletar campo mascarado ──────────────────────────────────────────
        elif c == 41:
            print(f"\n  🔒 [{desc_cmd} | TC:{tc}]  min:{mn}  max:{mx}")
            if msg:
                print(f"     {msg}")
            import getpass
            entrada = getpass.getpass("     >> ").strip()
            responder(buffer, entrada)

        # ── Comando desconhecido — mostra tudo e passa vazio ─────────────────
        else:
            print(f"  ❓ [Cmd:{c} | TC:{tc} | min:{mn} max:{mx}] {repr(msg)}")
            entrada = input("     >> Entrada (Enter=vazio): ").strip()
            responder(buffer, entrada)


# ─────────────────────────────────────────────────────────────────────────────
# SALVAR DADOS DA TRANSAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

DADOS_DIR = os.path.join(LIB_DIR, "transacoes")

def _salvar_dados(cupom, data, hora, nome, funcao, valor, ret_loop,
                  dados_transacao: dict, linhas_cupom: list):
    os.makedirs(DADOS_DIR, exist_ok=True)

    campos = {
        str(tc): {
            "descricao": TIPO_CAMPO.get(tc, f"Campo desconhecido TC:{tc}"),
            "valor": v,
        }
        for tc, v in sorted(dados_transacao.items())
    }

    registro = {
        "cupom":        cupom,
        "data":         data,
        "hora":         hora,
        "transacao":    nome,
        "funcao":       funcao,
        "valor":        valor,
        "resultado":    ret_loop,
        "aprovada":     ret_loop == 0,
        "campos":       campos,
        "cupom_linhas": linhas_cupom,
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = os.path.join(DADOS_DIR, f"transacao_{ts}_cupom{cupom}.json")
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        json.dump(registro, f, ensure_ascii=False, indent=2)
    print(f"  💾 Dados salvos em: {nome_arquivo}")


# ─────────────────────────────────────────────────────────────────────────────
# TRANSAÇÃO COMPLETA (Inicia → Loop → Finaliza)
# ─────────────────────────────────────────────────────────────────────────────

def executar_transacao(lib, nome: str, funcao: int, valor: str = "0,00"):
    sep("═")
    print(f"  TRANSAÇÃO: {nome}")
    print(f"  Funcao={funcao} | Valor=R${valor}")
    sep("═")

    cupom = proximo_cupom()
    data  = now_date()
    hora  = now_time()

    print(f"  Cupom: {cupom} | Data: {data} | Hora: {hora}\n")

    # ── FASE 2: Iniciar ──────────────────────────────────────────────────────
    resultado = mk_buf(8)

    lib.IniciaFuncaoSiTefInterativoA(
        resultado,
        b(str(funcao).rjust(6, "0")),
        b(valor),
        b(cupom),
        b(data),
        b(hora),
        b(OPERADOR),
        b(""),          # ParamAdic — vazio para testes básicos
    )

    ret = ascii_resultado(resultado)
    status(ret, "IniciaFuncaoSiTefInterativoA")

    if ret != 10000:
        return ret

    # ── FASE 3: Loop ─────────────────────────────────────────────────────────
    dados_transacao: dict = {}
    ret_loop, houve_cupom, linhas_cupom = executar_loop(lib, dados_transacao)

    sep()
    status(ret_loop, "Resultado do loop")

    # ── FASE 4: Finalizar ────────────────────────────────────────────────────
    # FinalizaFuncao deve ser chamada SEMPRE após o fim do loop (ret != 10000),
    # tanto para sucesso quanto para erro. Confirma=1 confirma a transação,
    # Confirma=0 desfaz — necessário para liberar o estado interno da lib
    # e evitar -12 ("loop anterior não terminou") na próxima chamada.
    if ret_loop == 0:
        if houve_cupom and linhas_cupom:
            sep()
            print("  🖨️  CUPOM TEF:")
            sep("·")
            for linha in linhas_cupom:
                print(f"  {linha}")
            sep("·")
            imp_ok = input("  Cupom impresso OK? (S/N): ").strip().upper()
            confirma = 1 if imp_ok != "N" else 0
        else:
            confirma = 1
    else:
        confirma = 0

    # ── RESUMO E SALVAMENTO — antes do Finaliza para sobreviver a segfaults ──
    if ret_loop == 0:
        print("  ✅  TRANSAÇÃO APROVADA")
    else:
        desc = ERROS_GERAIS.get(ret_loop, f"Código {ret_loop}")
        print(f"  ❌  TRANSAÇÃO NÃO APROVADA — {desc}")

    if dados_transacao:
        sep()
        print("  DADOS RECEBIDOS DO SERVIDOR (TipoCampo=0)")
        sep("·")
        for tc_num, valor in sorted(dados_transacao.items()):
            desc_tc = TIPO_CAMPO.get(tc_num, f"Campo desconhecido TC:{tc_num}")
            print(f"  TC {tc_num:>5}  {desc_tc:<50}  {valor!r}")
        sep("·")

    _salvar_dados(cupom, data, hora, nome, funcao, valor, ret_loop, dados_transacao, linhas_cupom)

    # ── FASE 4: Finalizar ────────────────────────────────────────────────────
    resultado_fin = mk_buf(8)
    confirma_buf = ctypes.create_string_buffer(b(str(confirma).rjust(6, "0")), 8)
    lib.FinalizaFuncaoSiTefInterativoA(
        resultado_fin,
        confirma_buf,
    )
    ret_fin = ascii_resultado(resultado_fin)
    status(ret_fin, f"FinalizaFuncaoSiTefInterativoA(Confirma={confirma})")

    sep("═")

    return ret_loop


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICAR PENDÊNCIAS
# ─────────────────────────────────────────────────────────────────────────────

def verificar_pendencias(lib):
    sep("═")
    print("  VERIFICAR PENDÊNCIAS")
    sep("═")
    cupom = input(f"  Número do cupom fiscal: ").strip()
    data  = input(f"  Data fiscal (AAAAMMDD) [{now_date()}]: ").strip() or now_date()

    if not cupom:
        print("  ⚠️  Número do cupom é obrigatório")
        return

    resultado = mk_buf(8)
    buf_cupom = ctypes.create_string_buffer(b(cupom), len(cupom) + 2)
    buf_data  = ctypes.create_string_buffer(b(data),  len(data)  + 2)
    lib.ObtemQuantidadeTransacoesPendentesA(resultado, buf_cupom, buf_data)
    ret = ascii_resultado(resultado)

    sep()
    if ret == -13:
        print("  ✅ Nenhuma pendência — documento fiscal não registrado")
    elif ret == 0:
        print("  ✅ 0 transações pendentes para este documento")
    elif ret > 0:
        print(f"  ⚠️  {ret} transação(ões) pendente(s) de confirmação")
        print("     Execute a(s) transação(ões) para resolver antes de continuar")
    else:
        desc = ERROS_GERAIS.get(ret, f"Código {ret}")
        print(f"  ❌ Erro: {desc}")
    sep("═")


# ─────────────────────────────────────────────────────────────────────────────
# MENU PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def menu(lib):
    opcoes = list(FUNCOES.items())

    while True:
        sep("═")
        print("  CLISITEF TEST SUITE")
        print(f"  SiTef: {IP_SITEF}:4096  |  Loja: {ID_LOJA}  |  Terminal: {ID_TERMINAL}")
        sep("═")

        for i, (nome, (funcao, _)) in enumerate(opcoes, 1):
            print(f"  {i:2d}. {nome:<40} (F={funcao})")

        sep()
        print("   P. Verificar pendências de confirmação")
        print("   0. Sair")
        sep()

        escolha = input("  Opção: ").strip().upper()

        if escolha == "0":
            print("  Encerrando.")
            break

        elif escolha == "P":
            verificar_pendencias(lib)

        elif escolha.isdigit() and 1 <= int(escolha) <= len(opcoes):
            idx  = int(escolha) - 1
            nome, (funcao, pede_valor) = opcoes[idx]

            if pede_valor:
                v = input(f"  Valor da transação (Enter = 10,00): ").strip()
                valor = v if v else "10,00"
            else:
                valor = "0,00"

            executar_transacao(lib, nome, funcao, valor)
            input("\n  [Enter para continuar]")

        else:
            print("  ⚠️  Opção inválida")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sep("═")
    print("  CLISITEF TEST SUITE  —  v1.0")
    sep("═")

    lib = carregar_lib()
    print(f"  ✅ Biblioteca carregada")
    print(f"     {LIB_PATH}")

    if not configurar(lib):
        print("\n  ❌ Falha na configuração. Verifique:")
        print("     1. SiTef Simulado está rodando em sitef-server (192.168.10.12) ?")
        print("     2. Porta 4096 está acessível? (nc -zv sitef-server 4096)")
        print("     3. CliSiTef.ini está no mesmo diretório da .so ?")
        sys.exit(1)

    menu(lib)
