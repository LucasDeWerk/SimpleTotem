from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from core.config import DATABASE_URL
from core.schema_migrations import run_schema_migrations

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # required for SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_schema() -> None:
    """Migrações leves para SQLite (colunas novas sem Alembic)."""
    from models.orm import ApiSessao, Hardware, SaidaPagamento, SyncCheckpoint

    Base.metadata.create_all(
        bind=engine,
        tables=[ApiSessao.__table__, SyncCheckpoint.__table__, SaidaPagamento.__table__],
    )
    with engine.begin() as conn:
        cols = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(tconf_hardware)")).fetchall()
        }
        if cols and "driver_id" not in cols:
            conn.execute(text("ALTER TABLE tconf_hardware ADD COLUMN driver_id TEXT"))

        sessao_cols = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(tconf_api_sessao)")).fetchall()
        }
        for col in ("senha_simples_enc", "senha_os_enc"):
            if sessao_cols and col not in sessao_cols:
                conn.execute(text(f"ALTER TABLE tconf_api_sessao ADD COLUMN {col} TEXT"))

        empresa_cols = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(vstb_empresa)")).fetchall()
        }
        for col in ("email_simples", "senha_simples", "usuario_os", "senha_os"):
            if empresa_cols and col not in empresa_cols:
                conn.execute(text(f"ALTER TABLE vstb_empresa ADD COLUMN {col} TEXT"))

        run_schema_migrations(conn)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

