"""Resolução do terminal do totem (tven_terminal)."""

from __future__ import annotations

import socket
from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


def _local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def resolver_terminal_atual(db: Session, client_ip: Optional[str] = None) -> Optional[Dict[str, Any]]:
    ip = (client_ip or _local_ip()).strip()
    row = db.execute(
        text("""
            SELECT id, descterminal, nome_dispositivo, ip_dispositivo,
                   totem_autoatendimento, imprime_pedido
            FROM tven_terminal
            WHERE ip_dispositivo = :ip
            LIMIT 1
        """),
        {"ip": ip},
    ).mappings().first()

    if not row:
        row = db.execute(
            text("""
                SELECT id, descterminal, nome_dispositivo, ip_dispositivo,
                       totem_autoatendimento, imprime_pedido
                FROM tven_terminal
                WHERE totem_autoatendimento = 'S'
                ORDER BY id
                LIMIT 1
            """)
        ).mappings().first()

    if not row:
        row = db.execute(
            text("""
                SELECT id, descterminal, nome_dispositivo, ip_dispositivo,
                       totem_autoatendimento, imprime_pedido
                FROM tven_terminal
                ORDER BY id
                LIMIT 1
            """)
        ).mappings().first()

    return dict(row) if row else None
