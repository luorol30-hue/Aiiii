import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SoilTest


def latest_soil_snapshot(db: Session, field_id: uuid.UUID | None) -> dict | None:
    if not field_id:
        return None
    soil = db.scalar(
        select(SoilTest).where(SoilTest.field_id == field_id).order_by(SoilTest.tested_at.desc())
    )
    if not soil:
        return None
    return {
        "tested_at": soil.tested_at.isoformat(),
        "ph": float(soil.ph) if soil.ph is not None else None,
        "nitrogen_ppm": float(soil.nitrogen_ppm) if soil.nitrogen_ppm is not None else None,
        "phosphorus_ppm": float(soil.phosphorus_ppm) if soil.phosphorus_ppm is not None else None,
        "potassium_ppm": float(soil.potassium_ppm) if soil.potassium_ppm is not None else None,
        "organic_carbon_pct": (
            float(soil.organic_carbon_pct) if soil.organic_carbon_pct is not None else None
        ),
        "moisture_pct": float(soil.moisture_pct) if soil.moisture_pct is not None else None,
        "raw_result": soil.raw_result,
    }
