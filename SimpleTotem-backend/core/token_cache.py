import logging

from fastapi import FastAPI

logger = logging.getLogger(__name__)


async def fetch_and_cache_token(app: FastAPI):
    """Token SimpleSfique vem do login em /sinc/simplesfique/login — nada automático aqui."""
    app.state.external_api_token = getattr(app.state, "external_api_token", None)
    return bool(app.state.external_api_token)


def get_cached_token(app: FastAPI) -> str:
    """Retorna o token armazenado em cache."""
    return getattr(app.state, "external_api_token", None)
