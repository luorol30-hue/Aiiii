from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Report, User
from app.schemas import ReportOut
from app.security import get_current_user

router = APIRouter()


@router.get("", response_model=list[ReportOut])
def list_reports(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Report]:
    return list(
        db.scalars(
            select(Report).where(Report.user_id == current_user.id).order_by(Report.created_at.desc())
        )
    )
