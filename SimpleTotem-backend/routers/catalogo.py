from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.orm import Grupo, Subgrupo, Produto
from models.schemas import GrupoOut, SubgrupoOut, ProdutoOut

router = APIRouter(prefix="/catalogo", tags=["catalogo"])


# ── Grupos ────────────────────────────────────────────────────────────────────

@router.get("/grupos", response_model=List[GrupoOut])
def list_grupos(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    return db.query(Grupo).all()


@router.get("/grupos/{id_grupo}", response_model=GrupoOut)
def get_grupo(
    id_grupo: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    grupo = db.query(Grupo).filter(Grupo.id_grupo == id_grupo).first()
    if not grupo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grupo não encontrado")
    return grupo


# ── Subgrupos ─────────────────────────────────────────────────────────────────

@router.get("/subgrupos", response_model=List[SubgrupoOut])
def list_subgrupos(
    id_grupo: Optional[int] = Query(None, description="Filtrar por grupo"),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    q = db.query(Subgrupo)
    if id_grupo is not None:
        q = q.filter(Subgrupo.id_grupo == id_grupo)
    return q.all()


# ── Produtos ──────────────────────────────────────────────────────────────────

@router.get("/produtos", response_model=List[ProdutoOut])
def list_produtos(
    id_grupo: Optional[int] = Query(None),
    id_subgrupo: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    q = db.query(Produto)
    if id_grupo is not None:
        q = q.filter(Produto.id_grupo == id_grupo)
    if id_subgrupo is not None:
        q = q.filter(Produto.id_subgrupo == id_subgrupo)
    return q.all()


@router.get("/produtos/{id_produto}", response_model=ProdutoOut)
def get_produto(
    id_produto: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    produto = db.query(Produto).filter(Produto.id_produto == id_produto).first()
    if not produto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    return produto

