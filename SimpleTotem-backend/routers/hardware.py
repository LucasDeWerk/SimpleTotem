from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.orm import Hardware
from models.schemas import (
    CPUInfo, MemoryInfo, DiskInfo,
    HardwareDBOut, HardwareDBCreate, HardwareDBUpdate, HardwareAtribuir,
)
from services import device_service, hardware_service, impressora_service, pinpad_service

router = APIRouter(prefix="/hardware", tags=["hardware"])


# ── psutil ────────────────────────────────────────────────────────────────────

@router.get("/cpu", response_model=CPUInfo)
def get_cpu(current_user: str = Depends(get_current_user)) -> CPUInfo:
    try:
        return hardware_service.get_cpu_usage()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/memory", response_model=MemoryInfo)
def get_memory(current_user: str = Depends(get_current_user)) -> MemoryInfo:
    try:
        return hardware_service.get_memory_info()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/disk", response_model=DiskInfo)
def get_disk(current_user: str = Depends(get_current_user)) -> DiskInfo:
    try:
        return hardware_service.get_disk_info()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ── Dispositivos genéricos (qualquer marca / VID:PID) ─────────────────────────

@router.get("/tipos")
def get_tipos(_: str = Depends(get_current_user)):
    try:
        return {"tipos": device_service.listar_categorias()}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/catalogo")
def get_catalogo(_: str = Depends(get_current_user)):
    """Compat — retorna tipos de periférico, não lista fechada de marcas."""
    try:
        return {"tipos": device_service.listar_categorias()}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/atribuir")
def atribuir_dispositivo(payload: HardwareAtribuir, _: str = Depends(get_current_user)):
    try:
        return device_service.atribuir_dispositivo(
            categoria=payload.categoria,
            vendor_id=payload.vendor_id,
            product_id=payload.product_id,
            nome=payload.nome,
            fabricante=payload.fabricante,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.delete("/atribuir/{categoria}", status_code=status.HTTP_204_NO_CONTENT)
def remover_atribuicao(categoria: str, _: str = Depends(get_current_user)):
    device_service.remover_dispositivo(categoria)


@router.get("/status")
def get_status_geral(_: str = Depends(get_current_user)):
    try:
        return device_service.status_geral()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/status/{categoria}")
def get_status_categoria(categoria: str, _: str = Depends(get_current_user)):
    try:
        return device_service.status_categoria(categoria)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/configurar/{driver_id}")
def configurar_driver(driver_id: str, _: str = Depends(get_current_user)):
    try:
        return device_service.configurar_driver(driver_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/configurar-categoria/{categoria}")
def configurar_categoria(categoria: str, _: str = Depends(get_current_user)):
    try:
        return device_service.configurar_categoria(categoria)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ── Compat: impressora / pinpad ────────────────────────────────────────────────

@router.get("/impressora/status")
def get_impressora_status(
    driver_id: Optional[str] = Query(None),
    _: str = Depends(get_current_user),
):
    try:
        return impressora_service.status_impressora(driver_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/impressora/configurar")
def configurar_impressora(
    driver_id: Optional[str] = Query(None),
    _: str = Depends(get_current_user),
):
    try:
        return impressora_service.configurar_impressora(driver_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/pinpad/status")
def get_pinpad_status(_: str = Depends(get_current_user)):
    try:
        return pinpad_service.status_pinpad()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/pinpad/configurar")
def configurar_pinpad(
    driver_id: Optional[str] = Query(None),
    _: str = Depends(get_current_user),
):
    try:
        return pinpad_service.configurar_pinpad(driver_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ── tconf_hardware (DB) ───────────────────────────────────────────────────────

@router.get("/dispositivos", response_model=List[HardwareDBOut])
def list_dispositivos(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    return db.query(Hardware).all()


@router.get("/dispositivos/{id}", response_model=HardwareDBOut)
def get_dispositivo(
    id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    hw = db.query(Hardware).filter(Hardware.id == id).first()
    if not hw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo não encontrado")
    return hw


@router.post("/dispositivos", response_model=HardwareDBOut, status_code=status.HTTP_201_CREATED)
def create_dispositivo(
    payload: HardwareDBCreate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    now = datetime.now(timezone.utc).isoformat()
    hw = Hardware(**payload.model_dump(), dhinc=now)
    db.add(hw)
    db.commit()
    db.refresh(hw)
    return hw


@router.patch("/dispositivos/{id}", response_model=HardwareDBOut)
def update_dispositivo(
    id: int,
    payload: HardwareDBUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    hw = db.query(Hardware).filter(Hardware.id == id).first()
    if not hw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo não encontrado")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(hw, field, value)
    hw.dhalt = datetime.now(timezone.utc).isoformat()
    db.commit()
    db.refresh(hw)
    return hw


@router.delete("/dispositivos/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dispositivo(
    id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    hw = db.query(Hardware).filter(Hardware.id == id).first()
    if not hw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo não encontrado")
    db.delete(hw)
    db.commit()
