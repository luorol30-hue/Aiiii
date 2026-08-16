import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CHAR, JSON, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db import Base

JSONType = JSON().with_variant(JSONB, "postgresql")


class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PostgresUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        if not isinstance(value, uuid.UUID):
            return str(uuid.UUID(str(value)))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None or isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(String, unique=True)
    phone: Mapped[str | None] = mapped_column(String, unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text)
    google_subject: Mapped[str | None] = mapped_column(String, unique=True)
    full_name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="farmer")
    locale: Mapped[str] = mapped_column(String, default="en")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    farms: Mapped[list["Farm"]] = relationship(back_populates="owner")


class Farm(Base, TimestampMixin):
    __tablename__ = "farms"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String)
    country: Mapped[str] = mapped_column(String)
    region: Mapped[str | None] = mapped_column(String)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    area_hectares: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))

    owner: Mapped[User] = relationship(back_populates="farms")
    fields: Mapped[list["FarmField"]] = relationship(back_populates="farm")


class FarmField(Base, TimestampMixin):
    __tablename__ = "farm_fields"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    farm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String)
    boundary_geojson: Mapped[dict | None] = mapped_column(JSONType)
    soil_type: Mapped[str | None] = mapped_column(String)
    area_hectares: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))

    farm: Mapped[Farm] = relationship(back_populates="fields")


class Crop(Base, TimestampMixin):
    __tablename__ = "crops"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String)
    variety: Mapped[str | None] = mapped_column(String)
    scientific_name: Mapped[str | None] = mapped_column(String)


class CropCycle(Base, TimestampMixin):
    __tablename__ = "crop_cycles"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    field_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farm_fields.id", ondelete="CASCADE"))
    crop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("crops.id"))
    planted_at: Mapped[date] = mapped_column(Date)
    expected_harvest_at: Mapped[date | None] = mapped_column(Date)
    harvested_at: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String, default="active")


class SoilTest(Base):
    __tablename__ = "soil_tests"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    field_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farm_fields.id", ondelete="CASCADE"))
    tested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ph: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    nitrogen_ppm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    phosphorus_ppm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    potassium_ppm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    organic_carbon_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    moisture_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    lab_report_url: Mapped[str | None] = mapped_column(Text)
    raw_result: Mapped[dict] = mapped_column(JSONType, default=dict)


class SensorDevice(Base):
    __tablename__ = "sensor_devices"
    __table_args__ = (UniqueConstraint("provider", "external_device_id"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    field_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farm_fields.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String)
    external_device_id: Mapped[str] = mapped_column(String)
    device_type: Mapped[str] = mapped_column(String)
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String, default="active")
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONType, default=dict)


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sensor_devices.id", ondelete="CASCADE"))
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    metric: Mapped[str] = mapped_column(String)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    unit: Mapped[str] = mapped_column(String)
    raw_payload: Mapped[dict] = mapped_column(JSONType, default=dict)


class DiseaseDetection(Base, TimestampMixin):
    __tablename__ = "disease_detections"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    farm_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("farms.id", ondelete="SET NULL"))
    field_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("farm_fields.id", ondelete="SET NULL"))
    crop_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("crops.id", ondelete="SET NULL"))
    image_url: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String)
    disease_label: Mapped[str] = mapped_column(String)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 5))
    affected_area_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    severity: Mapped[str] = mapped_column(String)
    weather_snapshot: Mapped[dict | None] = mapped_column(JSONType)
    soil_snapshot: Mapped[dict | None] = mapped_column(JSONType)
    recommendation: Mapped[dict] = mapped_column(JSONType)
    raw_prediction: Mapped[dict] = mapped_column(JSONType)


class Treatment(Base, TimestampMixin):
    __tablename__ = "treatments"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    disease_detection_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("disease_detections.id", ondelete="SET NULL")
    )
    crop_cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("crop_cycles.id", ondelete="SET NULL")
    )
    treatment_type: Mapped[str] = mapped_column(String)
    product_name: Mapped[str | None] = mapped_column(String)
    dosage: Mapped[str | None] = mapped_column(String)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class FertilizerPlan(Base, TimestampMixin):
    __tablename__ = "fertilizer_plans"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    crop_cycle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("crop_cycles.id", ondelete="CASCADE"))
    generated_from_soil_test_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("soil_tests.id", ondelete="SET NULL")
    )
    plan: Mapped[dict] = mapped_column(JSONType)


class IrrigationPlan(Base, TimestampMixin):
    __tablename__ = "irrigation_plans"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    crop_cycle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("crop_cycles.id", ondelete="CASCADE"))
    plan: Mapped[dict] = mapped_column(JSONType)


class WeatherHistory(Base, TimestampMixin):
    __tablename__ = "weather_history"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    farm_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSONType)


class YieldPrediction(Base, TimestampMixin):
    __tablename__ = "yield_predictions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    crop_cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("crop_cycles.id", ondelete="SET NULL")
    )
    disease_detection_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("disease_detections.id", ondelete="SET NULL")
    )
    model_name: Mapped[str] = mapped_column(String)
    predicted_yield_tonnes_per_hectare: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    impact_pct: Mapped[Decimal | None] = mapped_column(Numeric(7, 3))
    features: Mapped[dict] = mapped_column(JSONType)
    raw_prediction: Mapped[dict] = mapped_column(JSONType)


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    farm_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("farms.id", ondelete="SET NULL"))
    report_type: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    file_url: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONType, default=dict)


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    channel: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending")
    payload: Mapped[dict] = mapped_column(JSONType, default=dict)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String)
    external_subscription_id: Mapped[str | None] = mapped_column(String)
    plan_name: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ChatHistory(Base, TimestampMixin):
    __tablename__ = "chat_history"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    farm_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("farms.id", ondelete="SET NULL"))
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONType, default=dict)


class AiPrediction(Base, TimestampMixin):
    __tablename__ = "ai_predictions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    prediction_type: Mapped[str] = mapped_column(String)
    model_name: Mapped[str] = mapped_column(String)
    input_refs: Mapped[dict] = mapped_column(JSONType)
    output: Mapped[dict] = mapped_column(JSONType)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 5))


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    crop_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("crops.id", ondelete="SET NULL"))
    market_name: Mapped[str] = mapped_column(String)
    region: Mapped[str | None] = mapped_column(String)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    currency: Mapped[str] = mapped_column(String)
    unit: Mapped[str] = mapped_column(String)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String)
    raw_payload: Mapped[dict] = mapped_column(JSONType, default=dict)


class Equipment(Base, TimestampMixin):
    __tablename__ = "equipment"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    farm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String)
    equipment_type: Mapped[str] = mapped_column(String)
    manufacturer: Mapped[str | None] = mapped_column(String)
    model: Mapped[str | None] = mapped_column(String)
    purchased_at: Mapped[date | None] = mapped_column(Date)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONType, default=dict)
