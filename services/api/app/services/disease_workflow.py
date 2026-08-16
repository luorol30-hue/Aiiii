import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import TypedDict

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ExternalServiceNotConfigured
from app.models import User
from app.services.ai import (
    DiseaseModel,
    DiseaseModelResult,
    ImageAnalyzer,
    RecommendationEngine,
    YieldImpactModel,
)
from app.services.soil import latest_soil_snapshot
from app.services.storage import ObjectStorage
from app.services.weather import WeatherClient


class DiseaseWorkflowState(TypedDict, total=False):
    db: Session
    settings: Settings
    user: User
    image: UploadFile
    farm_id: uuid.UUID | None
    field_id: uuid.UUID | None
    crop_id: uuid.UUID | None
    latitude: float | None
    longitude: float | None
    image_url: str
    prediction: DiseaseModelResult
    affected_area_pct: Decimal | None
    weather: dict | None
    soil: dict | None
    yield_impact: dict | None
    severity: str
    recommendation: dict


@dataclass
class DiseaseWorkflowResult:
    image_url: str
    prediction: DiseaseModelResult
    affected_area_pct: Decimal | None
    weather: dict | None
    soil: dict | None
    yield_impact: dict | None
    severity: str
    recommendation: dict


class DiseaseDetectionWorkflow:
    async def run(
        self,
        db: Session,
        settings: Settings,
        user: User,
        image: UploadFile,
        farm_id: uuid.UUID | None,
        field_id: uuid.UUID | None,
        crop_id: uuid.UUID | None,
        latitude: float | None,
        longitude: float | None,
    ) -> DiseaseWorkflowResult:
        graph = self._build_graph()
        state = await graph.ainvoke(
            {
                "db": db,
                "settings": settings,
                "user": user,
                "image": image,
                "farm_id": farm_id,
                "field_id": field_id,
                "crop_id": crop_id,
                "latitude": latitude,
                "longitude": longitude,
            }
        )
        return DiseaseWorkflowResult(
            image_url=state["image_url"],
            prediction=state["prediction"],
            affected_area_pct=state.get("affected_area_pct"),
            weather=state.get("weather"),
            soil=state.get("soil"),
            yield_impact=state.get("yield_impact"),
            severity=state["severity"],
            recommendation=state["recommendation"],
        )

    def _build_graph(self):
        try:
            from langgraph.graph import END, StateGraph
        except ImportError as exc:
            raise ExternalServiceNotConfigured("langgraph is not installed") from exc

        workflow = StateGraph(DiseaseWorkflowState)
        workflow.add_node("store_image", self._store_image)
        workflow.add_node("detect_disease", self._detect_disease)
        workflow.add_node("measure_area", self._measure_area)
        workflow.add_node("fetch_weather", self._fetch_weather)
        workflow.add_node("load_soil", self._load_soil)
        workflow.add_node("predict_yield_impact", self._predict_yield_impact)
        workflow.add_node("recommend", self._recommend)

        workflow.set_entry_point("store_image")
        workflow.add_edge("store_image", "detect_disease")
        workflow.add_edge("detect_disease", "measure_area")
        workflow.add_edge("measure_area", "fetch_weather")
        workflow.add_edge("fetch_weather", "load_soil")
        workflow.add_edge("load_soil", "predict_yield_impact")
        workflow.add_edge("predict_yield_impact", "recommend")
        workflow.add_edge("recommend", END)
        return workflow.compile()

    def _store_image(self, state: DiseaseWorkflowState) -> dict:
        return {
            "image_url": ObjectStorage(state["settings"]).upload_leaf_image(
                state["image"], str(state["user"].id)
            )
        }

    def _detect_disease(self, state: DiseaseWorkflowState) -> dict:
        return {"prediction": DiseaseModel(state["settings"]).predict(state["image"])}

    def _measure_area(self, state: DiseaseWorkflowState) -> dict:
        return {
            "affected_area_pct": ImageAnalyzer().affected_area_pct(
                state["image"], state["prediction"].boxes
            )
        }

    async def _fetch_weather(self, state: DiseaseWorkflowState) -> dict:
        if state.get("latitude") is None or state.get("longitude") is None:
            return {"weather": None}
        return {
            "weather": await WeatherClient(state["settings"]).forecast(
                float(state["latitude"]), float(state["longitude"])
            )
        }

    def _load_soil(self, state: DiseaseWorkflowState) -> dict:
        return {"soil": latest_soil_snapshot(state["db"], state.get("field_id"))}

    def _predict_yield_impact(self, state: DiseaseWorkflowState) -> dict:
        soil = state.get("soil")
        impact = YieldImpactModel(state["settings"]).predict_impact(
            {
                "confidence": state["prediction"].confidence,
                "affected_area_pct": float(state.get("affected_area_pct") or Decimal("0")),
                "soil_ph": soil.get("ph") if soil else None,
                "soil_moisture_pct": soil.get("moisture_pct") if soil else None,
            }
        )
        return {"yield_impact": impact}

    def _recommend(self, state: DiseaseWorkflowState) -> dict:
        severity, recommendation = RecommendationEngine().build(
            state["prediction"].disease_label,
            state["prediction"].confidence,
            state.get("affected_area_pct"),
            state.get("weather"),
            state.get("soil"),
            state.get("yield_impact"),
        )
        return {"severity": severity, "recommendation": recommendation}
