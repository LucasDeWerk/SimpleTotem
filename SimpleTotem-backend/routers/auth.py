import getpass
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import create_access_token
from core.system_auth import authenticate_system_user
from models.schemas import TokenResponse, TotemLoginRequest
from services.empresa_credentials import update_os_credentials

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/login", response_model=TokenResponse)
def login() -> TokenResponse:
    """Retorna um token JWT para chamadas da API do totem (sem privilégios de admin)."""
    token = create_access_token(data={"sub": "totem", "role": "device"})
    return TokenResponse(access_token=token)


@router.get("/usuario-sugerido")
def usuario_sugerido():
    """Retorna o usuário local da sessão do backend (sugestão no formulário de login)."""
    return {"usuario": getpass.getuser()}


def _login_sistema(body: TotemLoginRequest, db: Session) -> TokenResponse:
    usuario = body.usuario.strip()
    senha = body.senha

    if not usuario or not senha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário e senha são obrigatórios",
        )

    try:
        autenticado = authenticate_system_user(usuario, senha)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if not autenticado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha do sistema inválidos",
        )

    token = create_access_token(data={"sub": usuario, "role": "admin"})
    try:
        update_os_credentials(db, usuario, senha)
    except Exception as exc:
        logger.warning("Não foi possível salvar credenciais OS na empresa: %s", exc)
    return TokenResponse(access_token=token)


@router.post("/system-login", response_model=TokenResponse)
def system_login(body: TotemLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Autentica com usuário e senha do computador (Linux/PAM)."""
    return _login_sistema(body, db)


@router.post("/totem-login", response_model=TokenResponse)
def totem_login(body: TotemLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Alias de system-login para compatibilidade."""
    return _login_sistema(body, db)
