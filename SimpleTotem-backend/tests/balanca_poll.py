"""Leitura contínua da balança Elgin (CH340, Toledo Prix): 2400 8N1 + ENQ.

Uso: python tests/balanca_poll.py [porta]   (Ctrl+C para sair)
Só imprime quando a leitura muda — coloque/tire peso e mexa no prato.
"""
import sys
import time

import serial

PORTA = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"


def interpretar(resp: bytes) -> str:
    if not resp:
        return "SEM RESPOSTA (balança não respondeu)"
    if resp[:1] == b"\x02" and resp[-1:] == b"\x03":
        corpo = resp[1:-1].decode("ascii", errors="replace")
        if corpo.isdigit():
            return f"PESO: {int(corpo)} g  ({int(corpo) / 1000:.3f} kg)   [bruto: {corpo}]"
        return f"ESTADO ESPECIAL (não é número): {corpo!r}  — pode ser instável/sobrecarga"
    return f"FORMATO DESCONHECIDO: {resp!r}"


with serial.Serial(PORTA, 2400, bytesize=8, parity="N", stopbits=1, timeout=0.5) as s:
    ultimo = None
    print(f"Lendo {PORTA} — Ctrl+C para sair\n")
    while True:
        s.reset_input_buffer()
        s.write(b"\x05")
        msg = interpretar(s.read(16))
        if msg != ultimo:
            print(f"{time.strftime('%H:%M:%S')}  {msg}")
            ultimo = msg
        time.sleep(0.2)
