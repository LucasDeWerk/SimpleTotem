"""Balança Elgin (CH340) — protocolo Toledo Prix, serial 2400 8N1.

Pergunta com ENQ (0x05); responde STX + 5 dígitos (gramas) + ETX,
ou STX + 'IIIII' + ETX enquanto o peso está instável.
"""
import json
import os
import re
import threading
import time
from collections import deque
from typing import Optional

import serial
from serial.tools import list_ports

from core.config import DATA_DIR

BALANCA_VID = 0x1A86
BALANCA_PID = 0x7523
BAUDRATE = 2400
ENQ = b"\x05"
LEITURAS_ESTAVEIS = 3
TIMEOUT_RESPOSTA_S = 0.6

_FRAME = re.compile(rb"\x02([0-9I]{5})\x03")

TARA_MAX_G = 10000
_TARA_FILE = DATA_DIR / "balanca.json"

_lock = threading.Lock()
_historico: deque[int] = deque(maxlen=LEITURAS_ESTAVEIS)


def interpretar_resposta(dados: bytes) -> dict:
    """Converte os bytes brutos em {status, peso_g}. Ignora lixo (ETX soltos) antes do frame."""
    m = _FRAME.search(dados or b"")
    if not m:
        return {"status": "sem_resposta" if not dados else "invalido", "peso_g": None}
    corpo = m.group(1)
    if corpo == b"IIIII":
        return {"status": "instavel", "peso_g": None}
    if corpo.isdigit():
        return {"status": "ok", "peso_g": int(corpo)}
    return {"status": "invalido", "peso_g": None}


def aplicar_tara(bruto_g: int, tara_g: int) -> int:
    """Peso líquido: bruto menos a tara, nunca negativo (prato retirado = 0)."""
    return max(0, bruto_g - tara_g)


def obter_tara() -> int:
    """Tara (g) salva pelo admin; 0 se não configurada ou arquivo ilegível."""
    try:
        return max(0, int(json.loads(_TARA_FILE.read_text())["tara_g"]))
    except (OSError, ValueError, KeyError, TypeError):
        return 0


def salvar_tara(tara_g: int) -> int:
    if not 0 <= tara_g <= TARA_MAX_G:
        raise ValueError(f"Tara deve estar entre 0 e {TARA_MAX_G} g")
    tmp = _TARA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"tara_g": int(tara_g)}))
    tmp.replace(_TARA_FILE)  # escrita atômica: nunca fica meio gravado
    return int(tara_g)


def capturar_tara() -> int:
    """Usa o peso bruto atual (prato vazio, estável e > 0) como tara."""
    leitura = ler_peso()
    if leitura["status"] != "ok" or not leitura["estavel"]:
        raise ValueError("Aguarde o peso estabilizar com o prato vazio na balança")
    if leitura["peso_bruto_g"] <= 0:
        raise ValueError("Coloque o prato vazio na balança")
    return salvar_tara(leitura["peso_bruto_g"])


def detectar_porta() -> Optional[str]:
    """BALANCA_PORT do .env tem prioridade; senão procura o CH340 (1a86:7523)."""
    porta = os.getenv("BALANCA_PORT", "").strip()
    if porta:
        return porta
    for p in list_ports.comports():
        if p.vid == BALANCA_VID and p.pid == BALANCA_PID:
            return p.device
    return None


def _ler_frame(s: serial.Serial) -> bytes:
    s.reset_input_buffer()
    s.write(ENQ)
    buf = b""
    fim = time.monotonic() + TIMEOUT_RESPOSTA_S
    while time.monotonic() < fim:
        buf += s.read(16)
        if _FRAME.search(buf):
            break
    return buf


def _resposta(status: str, bruto_g: Optional[int], estavel: bool, porta: Optional[str]) -> dict:
    tara = obter_tara()
    return {
        "status": status,
        "peso_bruto_g": bruto_g,
        "tara_g": tara,
        "peso_g": None if bruto_g is None else aplicar_tara(bruto_g, tara),
        "estavel": estavel,
        "porta": porta,
    }


def ler_peso() -> dict:
    """Uma leitura. Retorna {status, peso_bruto_g, tara_g, peso_g, estavel, porta}.

    peso_g é o líquido (bruto − tara). A estabilidade é medida no bruto.

    status: ok | instavel | sem_resposta | invalido | desconectada.
    `estavel` só é True com LEITURAS_ESTAVEIS leituras numéricas iguais seguidas.
    """
    porta = detectar_porta()
    if not porta:
        return _resposta("desconectada", None, False, None)
    with _lock:
        leitura = None
        for _tentativa in range(2):  # um soluço do USB não deve virar "desconectada"
            try:
                with serial.Serial(porta, BAUDRATE, bytesize=8, parity="N", stopbits=1, timeout=0.2) as s:
                    leitura = interpretar_resposta(_ler_frame(s))
                break
            except (serial.SerialException, OSError):
                time.sleep(0.05)
        if leitura is None:
            _historico.clear()
            return _resposta("desconectada", None, False, porta)
        if leitura["status"] == "ok":
            _historico.append(leitura["peso_g"])
        else:
            _historico.clear()
        estavel = (
            leitura["status"] == "ok"
            and len(_historico) == LEITURAS_ESTAVEIS
            and len(set(_historico)) == 1
        )
        return _resposta(leitura["status"], leitura["peso_g"], estavel, porta)
