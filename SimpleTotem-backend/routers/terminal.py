from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.schemas import TerminalOut
from services.terminal_service import resolver_terminal_atual

router = APIRouter(prefix="/terminal", tags=["terminal"])


@router.get("/atual", response_model=Optional[TerminalOut])
def terminal_atual(
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """Retorna o terminal deste totem (por IP ou primeiro autoatendimento)."""
    client_ip = request.client.host if request.client else None
    terminal = resolver_terminal_atual(db, client_ip)
    return terminal
