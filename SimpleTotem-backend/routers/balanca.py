from fastapi import APIRouter, Depends, HTTPException, status

from core.security import get_current_user
from models.schemas import BalancaLeitura
from services import balanca_service

router = APIRouter(prefix="/balanca", tags=["balanca"])


@router.get("/peso", response_model=BalancaLeitura)
def get_peso(_: str = Depends(get_current_user)) -> BalancaLeitura:
    """Leitura atual da balança. Chamar em polling (~300 ms) na tela de produto pesável."""
    try:
        return balanca_service.ler_peso()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
