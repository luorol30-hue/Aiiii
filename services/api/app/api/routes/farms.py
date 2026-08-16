from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Farm, User
from app.schemas import FarmCreate, FarmOut
from app.security import get_current_user

router = APIRouter()


@router.get("", response_model=list[FarmOut])
def list_farms(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Farm]:
    return list(db.scalars(select(Farm).where(Farm.owner_id == current_user.id).order_by(Farm.created_at.desc())))


@router.post("", response_model=FarmOut, status_code=status.HTTP_201_CREATED)
def create_farm(
    payload: FarmCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Farm:
    farm = Farm(owner_id=current_user.id, **payload.model_dump())
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm
