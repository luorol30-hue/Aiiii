from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Crop, User
from app.schemas import CropCreate, CropOut
from app.security import get_current_user

router = APIRouter()


@router.get("", response_model=list[CropOut])
def list_crops(
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Crop]:
    return list(db.scalars(select(Crop).order_by(Crop.name.asc())))


@router.post("", response_model=CropOut, status_code=status.HTTP_201_CREATED)
def create_crop(
    payload: CropCreate,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Crop:
    crop = Crop(**payload.model_dump())
    db.add(crop)
    db.commit()
    db.refresh(crop)
    return crop
