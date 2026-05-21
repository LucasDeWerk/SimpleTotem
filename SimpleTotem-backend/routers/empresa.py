from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.orm import Empresa
from models.schemas import EmpresaOut

router = APIRouter(prefix="/empresa", tags=["empresa"])


@router.get("", response_model=EmpresaOut)
def get_empresa(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    empresa = db.query(Empresa).first()
    if not empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    return empresa

