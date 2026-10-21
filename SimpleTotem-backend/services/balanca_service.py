"""Balança Elgin (CH340) — protocolo Toledo Prix, serial 2400 8N1.

Pergunta com ENQ (0x05); responde STX + 5 dígitos (gramas) + ETX,
ou STX + 'IIIII' + ETX enquanto o peso está instável.
"""
import os
import re
import threading
import time
from collections import deque
from typing import Optional

import serial
from serial.tools import list_ports

BALANCA_VID = 0x1A86
BALANCA_PID = 0x7523
BAUDRATE = 2400
ENQ = b"\x05"
LEITURAS_ESTAVEIS = 3
TIMEOUT_RESPOSTA_S = 0.6

_FRAME = re.compile(rb"\x02([0-9I]{5})\x03")

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


def ler_peso() -> dict:
    """Uma leitura. Retorna {status, peso_g, estavel, porta}.

    status: ok | instavel | sem_resposta | invalido | desconectada.
    `estavel` só é True com LEITURAS_ESTAVEIS leituras numéricas iguais seguidas.
    """
    porta = detectar_porta()
    if not porta:
        return {"status": "desconectada", "peso_g": None, "estavel": False, "porta": None}
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
            return {"status": "desconectada", "peso_g": None, "estavel": False, "porta": porta}
        if leitura["status"] == "ok":
            _historico.append(leitura["peso_g"])
        else:
            _historico.clear()
        estavel = (
            leitura["status"] == "ok"
            and len(_historico) == LEITURAS_ESTAVEIS
            and len(set(_historico)) == 1
        )
        return {**leitura, "estavel": estavel, "porta": porta}
