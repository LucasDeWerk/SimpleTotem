from fastapi import APIRouter

from core.security import create_access_token
from models.schemas import TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login() -> TokenResponse:
    """Retorna um token JWT válido por 1 dia, sem necessidade de credenciais."""
    token = create_access_token(data={"sub": "totem"})
    return TokenResponse(access_token=token)

