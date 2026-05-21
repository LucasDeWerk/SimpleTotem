import httpx
from fastapi import FastAPI
import time
from core.config import URL_API_TOKEN
import logging

logger = logging.getLogger(__name__)


async def fetch_and_cache_token(app: FastAPI):
    """Busca o token da API externa e armazena em app.state"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{URL_API_TOKEN}/vstsaaslogin",
                timeout=10.0,
            )
            response.raise_for_status()
            token_data = response.json()
            app.state.external_api_token = token_data.get("token")
            app.state.token_timestamp = time.time()
            
            token_preview = app.state.external_api_token[:20] + "..." if app.state.external_api_token else "None"
            logger.info(f"✓ Token sincronizado com sucesso | Token: {token_preview}")
            print(f"✓ Token sincronizado com sucesso | Token: {token_preview}")
            return True
    except Exception as e:
        logger.error(f"✗ Erro ao buscar token: {e}")
        print(f"✗ Erro ao buscar token: {e}")
        app.state.external_api_token = None
        app.state.token_timestamp = None
        return False


def get_cached_token(app: FastAPI) -> str:
    """Retorna o token armazenado em cache"""
    return getattr(app.state, 'external_api_token', None)
