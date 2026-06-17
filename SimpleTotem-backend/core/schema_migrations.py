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
    _migrate_vendas(conn)
    _migrate_produto_foto(conn)
    _migrate_api_sessao(conn)


def _migrate_vendas(conn: Connection) -> None:
    # DB-002: tven_saidapagamento
    if not _table_exists(conn, "tven_saidapagamento"):
        conn.execute(text("""
            CREATE TABLE tven_saidapagamento (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                id_saida INTEGER NOT NULL REFERENCES tven_saida(id),
                id_tipo_pagamento TEXT(2) REFERENCES tfin_tipopagrec(id),
                vlr_pagamento NUMERIC(17, 2) NOT NULL,
                nsu_sitef TEXT(20),
                nsu_host TEXT(20),
                autorizacao TEXT(20),
                bandeira TEXT(30),
                modalidade TEXT(30),
                pix INTEGER NOT NULL DEFAULT 0,
                cupom_bruto TEXT,
                dh_pagamento TEXT(19) NOT NULL
            )
        """))

    # DB-003: id_terminal em tven_saida
    saida_cols = _columns(conn, "tven_saida")
    if saida_cols and "id_terminal" not in saida_cols:
        conn.execute(text("ALTER TABLE tven_saida ADD COLUMN id_terminal INTEGER"))

    # DB-001: normalizar dtemissao para YYYY-MM-DD HH:MM:SS (SQLite não impõe TEXT(10))
    if saida_cols and "dtemissao" in saida_cols:
        conn.execute(text("""
            UPDATE tven_saida
            SET dtemissao = dtemissao || ' 00:00:00'
            WHERE length(trim(dtemissao)) = 10
        """))


def _migrate_produto_foto(conn: Connection) -> None:
    # DB-004: produtos sem foto — blob vazio em vez de NULL
    if _table_exists(conn, "test_produto"):
        conn.execute(text("UPDATE test_produto SET foto = X'' WHERE foto IS NULL"))
        conn.execute(text("""
            UPDATE test_produto SET custo_aquisicao = COALESCE(custo_aquisicao, custo_compra, custo_medio, 0)
            WHERE custo_aquisicao IS NULL
        """))
        conn.execute(text("""
            UPDATE test_produto SET custo_compra = COALESCE(custo_compra, custo_medio, custo_aquisicao, 0)
            WHERE custo_compra IS NULL
        """))
        conn.execute(text("""
            UPDATE test_produto SET custo_medio = COALESCE(custo_medio, custo_compra, custo_aquisicao, 0)
            WHERE custo_medio IS NULL
        """))
        conn.execute(text("UPDATE test_produto SET estoque = 0 WHERE estoque IS NULL"))
        conn.execute(text("""
            UPDATE test_produto SET dhinc = date('now') WHERE dhinc IS NULL OR dhinc = ''
        """))


def _migrate_api_sessao(conn: Connection) -> None:
    # DB-006: dhsinc como texto (campo legado na tabela)
    cols = _columns(conn, "tconf_api_sessao")
    if cols and "dhsinc" in cols:
        conn.execute(text("""
            UPDATE tconf_api_sessao
            SET dhsinc = strftime('%Y-%m-%d %H:%M:%S', dhsinc)
            WHERE dhsinc IS NOT NULL AND dhsinc NOT LIKE '%-%'
        """))
