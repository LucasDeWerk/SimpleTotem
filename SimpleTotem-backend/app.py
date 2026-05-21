from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from routers import auth, hardware, empresa, catalogo, vendas, sinc
from core.token_cache import fetch_and_cache_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - busca o token quando a app inicia
    await fetch_and_cache_token(app)
    yield
    # Shutdown - limpeza se necessário
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


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok"}
