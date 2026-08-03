"""Migrações SQLite incrementais (sem Alembic)."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection


def _table_exists(conn: Connection, name: str) -> bool:
    row = conn.execute(
        text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": name},
    ).fetchone()
    return row is not None


def _columns(conn: Connection, table: str) -> set[str]:
    if not _table_exists(conn, table):
        return set()
    return {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()}


def run_schema_migrations(conn: Connection) -> None:
    _migrate_api_sessao(conn)


def _migrate_api_sessao(conn: Connection) -> None:
    # DB-006: dhsinc como texto (campo legado na tabela)
    cols = _columns(conn, "tconf_api_sessao")
    if cols and "dhsinc" in cols:
        conn.execute(text("""
            UPDATE tconf_api_sessao
            SET dhsinc = strftime('%Y-%m-%d %H:%M:%S', dhsinc)
            WHERE dhsinc IS NOT NULL AND dhsinc NOT LIKE '%-%'
        """))
