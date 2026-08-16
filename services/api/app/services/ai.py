import os
import tempfile
from dataclasses import dataclass
from decimal import Decimal

import numpy as np
from fastapi import UploadFile

from app.core.config import Settings
from app.core.errors import ExternalServiceNotConfigured, ExternalServiceUnavailable

_YOLO_MODEL_CACHE: dict[str, object] = {}
_YIELD_MODEL_CACHE: dict[str, object] = {}


@dataclass
class DiseaseModelResult:
    model_name: str
    disease_label: str
    confidence: float
    boxes: list[dict]
    raw_prediction: dict


class DiseaseModel:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None

    def predict(self, file: UploadFile) -> DiseaseModelResult:
        if not self.settings.disease_model_path:
            raise ExternalServiceNotConfigured("DISEASE_MODEL_PATH is not configured")
        if not os.path.exists(self.settings.disease_model_path):
            raise ExternalServiceNotConfigured("DISEASE_MODEL_PATH does not exist")
        if self.settings.disease_model_type.lower() != "yolo":
            raise ExternalServiceNotConfigured(
                f"Unsupported DISEASE_MODEL_TYPE: {self.settings.disease_model_type}"
            )

        model = self._load_yolo()
        suffix = os.path.splitext(file.filename or "")[1] or ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            image_bytes = file.file.read()
            tmp.write(image_bytes)
            tmp_path = tmp.name
        file.file.seek(0)

        try:
            results = model.predict(tmp_path, verbose=False)
        except Exception as exc:
            raise ExternalServiceUnavailable("Disease model inference failed") from exc
        finally:
            os.unlink(tmp_path)

        if not results:
            raise ExternalServiceUnavailable("Disease model returned no predictions")

        first = results[0]
        names = getattr(first, "names", {})
        boxes = []
        best_label = "unknown"
        best_conf = 0.0
        for box in getattr(first, "boxes", []):
            cls_id = int(box.cls.item())
            confidence = float(box.conf.item())
            label = names.get(cls_id, str(cls_id))
            xyxy = [float(value) for value in box.xyxy[0].tolist()]
            boxes.append({"label": label, "confidence": confidence, "xyxy": xyxy})
            if confidence > best_conf:
                best_conf = confidence
                best_label = label

        return DiseaseModelResult(
            model_name=os.path.basename(self.settings.disease_model_path),
            disease_label=best_label,
            confidence=best_conf,
            boxes=boxes,
            raw_prediction={"boxes": boxes},
        )

    def _load_yolo(self):
        model_path = self.settings.disease_model_path
        if not model_path:
            raise ExternalServiceNotConfigured("DISEASE_MODEL_PATH is not configured")
        if model_path not in _YOLO_MODEL_CACHE:
            try:
                from ultralytics import YOLO
            except ImportError as exc:
                raise ExternalServiceNotConfigured("ultralytics is not installed") from exc
            _YOLO_MODEL_CACHE[model_path] = YOLO(model_path)
        return _YOLO_MODEL_CACHE[model_path]


class ImageAnalyzer:
    def affected_area_pct(self, file: UploadFile, boxes: list[dict]) -> Decimal | None:
        try:
            import cv2
        except ImportError as exc:
            raise ExternalServiceUnavailable("OpenCV runtime library missing") from exc

        image_bytes = np.frombuffer(file.file.read(), np.uint8)
        file.file.seek(0)
        image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
        if image is None:
            raise ExternalServiceUnavailable("Uploaded image could not be decoded")
        height, width = image.shape[:2]
        if height == 0 or width == 0 or not boxes:
            return None

        mask = np.zeros((height, width), dtype=np.uint8)
        for box in boxes:
            x1, y1, x2, y2 = [int(round(value)) for value in box["xyxy"]]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(width, x2), min(height, y2)
            if x2 > x1 and y2 > y1:
                mask[y1:y2, x1:x2] = 255

        affected_pixels = int(np.count_nonzero(mask))
        pct = (affected_pixels / float(width * height)) * 100
        return Decimal(str(round(pct, 3)))


class YieldImpactModel:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None

    def predict_impact(self, features: dict) -> dict | None:
        if not self.settings.yield_model_path:
            return None
        if not os.path.exists(self.settings.yield_model_path):
            raise ExternalServiceNotConfigured("YIELD_MODEL_PATH does not exist")
        try:
            import joblib
        except ImportError as exc:
            raise ExternalServiceNotConfigured("joblib is not installed") from exc
        if self.settings.yield_model_path not in _YIELD_MODEL_CACHE:
            _YIELD_MODEL_CACHE[self.settings.yield_model_path] = joblib.load(
                self.settings.yield_model_path
            )
        self._model = _YIELD_MODEL_CACHE[self.settings.yield_model_path]

        ordered_features = [
            float(features.get("confidence") or 0),
            float(features.get("affected_area_pct") or 0),
            float(features.get("soil_ph") or 0),
            float(features.get("soil_moisture_pct") or 0),
        ]
        try:
            prediction = self._model.predict([ordered_features])[0]
        except Exception as exc:
            raise ExternalServiceUnavailable("Yield model prediction failed") from exc
        return {"impact_pct": float(prediction), "features": ordered_features}


class RecommendationEngine:
    def build(
        self,
        disease_label: str,
        confidence: float,
        affected_area_pct: Decimal | None,
        weather: dict | None,
        soil: dict | None,
        yield_impact: dict | None,
    ) -> tuple[str, dict]:
        affected = float(affected_area_pct or 0)
        if confidence >= 0.85 and affected >= 15:
            severity = "high"
        elif confidence >= 0.65 or affected >= 5:
            severity = "medium"
        else:
            severity = "low"

        actions = [
            "Confirm the diagnosis with an agronomist before applying restricted chemicals.",
            "Isolate highly affected leaves and avoid overhead irrigation until reviewed.",
            "Re-scan this crop block after 48 hours and compare affected area percentage.",
        ]
        if weather:
            actions.append("Use the attached forecast to time treatment around rainfall and wind.")
        if soil:
            actions.append("Review the latest soil test before adding fertilizer to stressed plants.")
        if yield_impact:
            actions.append("Prioritize this block because the yield impact model flagged measurable risk.")

        return severity, {
            "summary": f"{disease_label} detected with {confidence:.2%} confidence.",
            "actions": actions,
            "yield_impact": yield_impact,
        }
