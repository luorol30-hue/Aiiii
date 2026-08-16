import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import (
    ExternalServiceNotConfigured,
    ExternalServiceUnavailable,
    service_not_configured,
    service_unavailable,
)
from app.db import get_db
from app.models import DiseaseDetection, User
from app.schemas import DetectionResponse
from app.security import get_current_user
from app.services.disease_workflow import DiseaseDetectionWorkflow
from app.services.notifications import NotificationService

router = APIRouter()


@router.post(
    "/disease-detections",
    response_model=DetectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_disease_detection(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    image: UploadFile = File(...),
    farm_id: uuid.UUID | None = Form(None),
    field_id: uuid.UUID | None = Form(None),
    crop_id: uuid.UUID | None = Form(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
) -> DiseaseDetection:
    try:
        result = await DiseaseDetectionWorkflow().run(
            db=db,
            settings=settings,
            user=current_user,
            image=image,
            farm_id=farm_id,
            field_id=field_id,
            crop_id=crop_id,
            latitude=latitude,
            longitude=longitude,
        )
    except ExternalServiceNotConfigured as exc:
        raise service_not_configured(str(exc)) from exc
    except ExternalServiceUnavailable as exc:
        raise service_unavailable(str(exc)) from exc

    detection = DiseaseDetection(
        user_id=current_user.id,
        farm_id=farm_id,
        field_id=field_id,
        crop_id=crop_id,
        image_url=result.image_url,
        model_name=result.prediction.model_name,
        disease_label=result.prediction.disease_label,
        confidence=Decimal(str(round(result.prediction.confidence, 5))),
        affected_area_pct=result.affected_area_pct,
        severity=result.severity,
        weather_snapshot=result.weather,
        soil_snapshot=result.soil,
        recommendation=result.recommendation,
        raw_prediction=result.prediction.raw_prediction,
    )
    db.add(detection)
    db.flush()

    if result.severity in {"medium", "high"}:
        NotificationService().create_action_notification(
            db,
            current_user,
            title=f"{result.severity.title()} crop health risk",
            body=result.recommendation["summary"],
            payload={"detection_id": str(detection.id), "severity": result.severity},
        )

    db.commit()
    db.refresh(detection)
    return detection
