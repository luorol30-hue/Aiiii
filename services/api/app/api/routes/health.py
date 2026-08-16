from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter()


@router.get("/health")
def health(db: Annotated[Session, Depends(get_db)]) -> dict:
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        print(f"Healthcheck DB ping failed: {exc}")
        db_ok = False
    return {"status": "ok", "database": "connected" if db_ok else "connecting"}
