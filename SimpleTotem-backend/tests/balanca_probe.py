"""Sonda da balança (CH340 / Elgin): descobre baudrate e formato dos dados brutos.

Uso: python tests/balanca_probe.py [porta]   (padrão: /dev/ttyUSB0)
Coloque um peso conhecido no prato antes de rodar.
"""
import sys
import time

import serial

PORTA = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
BAUDS = (9600, 4800, 2400, 19200, 1200)
COMANDOS = {"nenhum (só escuta)": None, "ENQ 0x05": b"\x05", "ENQ+CRLF": b"\x05\r\n", "'P'": b"P"}


def testar(baud: int, nome: str, cmd: bytes | None) -> bytes:
    with serial.Serial(PORTA, baud, bytesize=8, parity="N", stopbits=1, timeout=0.3) as s:
        s.reset_input_buffer()
        if cmd:
            s.write(cmd)
        fim = time.time() + 1.5
        dados = b""
        while time.time() < fim:
            dados += s.read(256)
        return dados


for baud in BAUDS:
    for nome, cmd in COMANDOS.items():
        try:
            dados = testar(baud, nome, cmd)
        except serial.SerialException as e:
            print(f"ERRO abrindo {PORTA}: {e}")
            sys.exit(1)
        print(f"{baud:>6} 8N1 | {nome:<18} | {len(dados):>3} bytes | {dados!r}")
