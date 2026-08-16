import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginRequest(BaseModel):
    id_token: str


class PhoneOtpSendRequest(BaseModel):
    phone: str


class PhoneOtpVerifyRequest(BaseModel):
    phone: str
    code: str
    full_name: str | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: str | None
    phone: str | None
    full_name: str
    role: str

    model_config = {"from_attributes": True}


class FarmCreate(BaseModel):
    name: str = Field(min_length=1)
    country: str = Field(min_length=2)
    region: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    area_hectares: Decimal | None = None


class FarmOut(FarmCreate):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class CropCreate(BaseModel):
    name: str = Field(min_length=1)
    variety: str | None = None
    scientific_name: str | None = None


class CropOut(CropCreate):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class WeatherResponse(BaseModel):
    provider: str
    latitude: float
    longitude: float
    payload: dict


class DetectionResponse(BaseModel):
    id: uuid.UUID
    image_url: str
    model_name: str
    disease_label: str
    confidence: Decimal
    affected_area_pct: Decimal | None
    severity: str
    recommendation: dict
    weather_snapshot: dict | None
    soil_snapshot: dict | None
    raw_prediction: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportOut(BaseModel):
    id: uuid.UUID
    report_type: str
    title: str
    file_url: str
    metadata_json: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationOut(BaseModel):
    id: uuid.UUID
    channel: str
    title: str
    body: str
    status: str
    payload: dict
    sent_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
