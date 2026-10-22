from fastapi import APIRouter, Depends, HTTPException, status

from core.security import get_current_user
from models.schemas import BalancaLeitura, BalancaTara
from services import balanca_service

router = APIRouter(prefix="/balanca", tags=["balanca"])


@router.get("/peso", response_model=BalancaLeitura)
def get_peso(_: str = Depends(get_current_user)) -> BalancaLeitura:
    """Leitura atual da balança. Chamar em polling (~300 ms) na tela de produto pesável."""
    try:
        return balanca_service.ler_peso()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/tara", response_model=BalancaTara)
def get_tara(_: str = Depends(get_current_user)) -> BalancaTara:
    return BalancaTara(tara_g=balanca_service.obter_tara())


@router.put("/tara", response_model=BalancaTara)
def put_tara(payload: BalancaTara, _: str = Depends(get_current_user)) -> BalancaTara:
    try:
        return BalancaTara(tara_g=balanca_service.salvar_tara(payload.tara_g))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post("/tara/capturar", response_model=BalancaTara)
def capturar_tara(_: str = Depends(get_current_user)) -> BalancaTara:
    """Define a tara com o peso atual da balança (prato vazio)."""
    try:
        return BalancaTara(tara_g=balanca_service.capturar_tara())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
