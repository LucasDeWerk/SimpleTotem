from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from routers import auth, hardware, empresa, catalogo, vendas, sinc, terminal
from core.database import ensure_schema
from services.device_service import bootstrap_hardware
from services.sitef_service import resolver_pendencias
from services.api_session import restore_session_to_app
from core.database import SessionLocal
from models.orm import Empresa


def _resolver_pendencias_startup() -> None:
    db = SessionLocal()
    try:
        empresa = db.query(Empresa).first()
        cnpj = (empresa.cpf_cnpj or "") if empresa else ""
        resolver_pendencias(cnpj_estabelecimento=cnpj)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_schema()
    bootstrap_hardware()
    _resolver_pendencias_startup()
    db = SessionLocal()
    try:
        restore_session_to_app(app, db)
    finally:
        db.close()
    yield
    app.state.external_api_token = None


app = FastAPI(
    title="Hardware API",
    description="Local FastAPI backend for hardware monitoring with JWT authentication",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # em produção restrinja para a origin do Electron
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(hardware.router)
app.include_router(empresa.router)
app.include_router(catalogo.router)
app.include_router(vendas.router)
app.include_router(sinc.router)
app.include_router(terminal.router)


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok"}
