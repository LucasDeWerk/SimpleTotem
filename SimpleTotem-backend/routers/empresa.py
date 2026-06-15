from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.orm import Empresa
from models.schemas import EmpresaOut, EmpresaStatusOut

router = APIRouter(prefix="/empresa", tags=["empresa"])


@router.get("/status", response_model=EmpresaStatusOut)
def get_empresa_status(db: Session = Depends(get_db)):
    """Verifica se o totem já possui empresa cadastrada (sem autenticação)."""
    try:
        configurada = db.query(Empresa).first() is not None
    except Exception:
        configurada = False
    return EmpresaStatusOut(configurada=configurada)


@router.get("", response_model=EmpresaOut)
def get_empresa(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    empresa = db.query(Empresa).first()
    if not empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    return empresa

