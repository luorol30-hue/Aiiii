import base64
import json
import os
import tempfile
from dataclasses import dataclass
from decimal import Decimal

import httpx
import numpy as np
from fastapi import UploadFile

from app.core.config import Settings
from app.core.errors import ExternalServiceNotConfigured, ExternalServiceUnavailable

_YOLO_MODEL_CACHE: dict[str, object] = {}
_YIELD_MODEL_CACHE: dict[str, object] = {}

AGRONOMY_VISION_PROMPT = (
    "You are a leading expert agricultural botanist and certified plant pathologist.\n"
    "Carefully analyze this uploaded farm crop, leaf, fruit, or tree photo.\n"
    "Diagnose the specific condition: disease name, pest infestation, fungal/bacterial pathogen, or nutrient deficiency.\n"
    "If the plant is completely healthy, indicate 'Healthy Plant (No Detected Disease)'.\n"
    "Respond with a valid JSON object matching this exact schema:\n"
    "{\n"
    '  "disease_label": "Common Disease Name (Scientific Name or Pathogen)",\n'
    '  "confidence": 0.95,\n'
    '  "severity": "low" | "medium" | "high",\n'
    '  "affected_area_pct": 20.0,\n'
    '  "summary": "Detailed botanical description of observed symptoms, lesions, leaf spotting, or discolouration.",\n'
    '  "actions": [\n'
    '    "Specific biological, organic, or chemical treatment with dosage recommendations",\n'
    '    "Immediate crop management, irrigation, or infected foliage removal step",\n'
    '    "Long-term soil, fertilization, or preventative protocol for adjacent crops"\n'
    '  ]\n'
    "}"
)


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
        # 1. Try Google Gemini Vision (100% Free Tier from Google AI Studio)
        if self.settings.gemini_api_key:
            gemini_res = self._analyze_with_gemini(file)
            if gemini_res:
                return gemini_res

        # 2. Try OpenAI Vision (GPT-4o / GPT-4o-mini)
        if self.settings.openai_api_key:
            openai_res = self._analyze_with_openai(file)
            if openai_res:
                return openai_res

        # 3. Try Groq Vision (Llama 3.2 Vision)
        if self.settings.groq_api_key:
            groq_res = self._analyze_with_groq(file)
            if groq_res:
                return groq_res

        # 4. Try local custom YOLO artifact if provided on disk
        if self.settings.disease_model_path and os.path.exists(self.settings.disease_model_path):
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

        # 5. Clear error explaining which AI keys can be connected
        if self.settings.openai_api_key or self.settings.gemini_api_key:
            raise ExternalServiceUnavailable(
                "Connected AI provider quota exceeded or failed. Please check your API key credits."
            )

        raise ExternalServiceNotConfigured(
            "No AI Vision key configured. Please add GEMINI_API_KEY (free from aistudio.google.com) or OPENAI_API_KEY to Railway variables."
        )

    def _analyze_with_gemini(self, file: UploadFile) -> DiseaseModelResult | None:
        file.file.seek(0)
        img_bytes = file.file.read()
        file.file.seek(0)
        b64_img = base64.b64encode(img_bytes).decode("utf-8")
        mime = file.content_type or "image/jpeg"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.settings.gemini_api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": AGRONOMY_VISION_PROMPT},
                        {"inline_data": {"mime_type": mime, "data": b64_img}},
                    ]
                }
            ],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.1},
        }

        try:
            with httpx.Client(timeout=35.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(raw_text)
                    disease_label = parsed.get("disease_label", "Plant Condition Identified")
                    confidence = float(parsed.get("confidence", 0.95))
                    return DiseaseModelResult(
                        model_name="google-gemini-1.5-flash-vision",
                        disease_label=disease_label,
                        confidence=confidence,
                        boxes=[{"label": disease_label, "confidence": confidence, "xyxy": [25.0, 25.0, 360.0, 360.0]}],
                        raw_prediction=parsed,
                    )
                else:
                    print(f"Gemini Vision API error ({res.status_code}): {res.text}")
        except Exception as exc:
            print(f"Gemini Vision request failed: {exc}")
        return None

    def _analyze_with_openai(self, file: UploadFile) -> DiseaseModelResult | None:
        file.file.seek(0)
        img_bytes = file.file.read()
        file.file.seek(0)
        b64_img = base64.b64encode(img_bytes).decode("utf-8")
        mime = file.content_type or "image/jpeg"

        try:
            with httpx.Client(timeout=35.0) as client:
                res = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": AGRONOMY_VISION_PROMPT},
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:{mime};base64,{b64_img}"},
                                    },
                                ],
                            }
                        ],
                        "temperature": 0.1,
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    disease_label = parsed.get("disease_label", "Plant Condition Identified")
                    confidence = float(parsed.get("confidence", 0.94))
                    return DiseaseModelResult(
                        model_name="openai-gpt-4o-vision",
                        disease_label=disease_label,
                        confidence=confidence,
                        boxes=[{"label": disease_label, "confidence": confidence, "xyxy": [30.0, 30.0, 350.0, 350.0]}],
                        raw_prediction=parsed,
                    )
                else:
                    print(f"OpenAI Vision API error ({res.status_code}): {res.text}")
        except Exception as exc:
            print(f"OpenAI Vision request failed: {exc}")
        return None

    def _analyze_with_groq(self, file: UploadFile) -> DiseaseModelResult | None:
        file.file.seek(0)
        img_bytes = file.file.read()
        file.file.seek(0)
        b64_img = base64.b64encode(img_bytes).decode("utf-8")
        mime = file.content_type or "image/jpeg"

        try:
            with httpx.Client(timeout=35.0) as client:
                res = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.settings.groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "llama-3.2-11b-vision-preview",
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": AGRONOMY_VISION_PROMPT},
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:{mime};base64,{b64_img}"},
                                    },
                                ],
                            }
                        ],
                        "temperature": 0.1,
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    disease_label = parsed.get("disease_label", "Plant Condition Identified")
                    confidence = float(parsed.get("confidence", 0.90))
                    return DiseaseModelResult(
                        model_name="groq-llama-3.2-vision",
                        disease_label=disease_label,
                        confidence=confidence,
                        boxes=[{"label": disease_label, "confidence": confidence, "xyxy": [30.0, 30.0, 350.0, 350.0]}],
                        raw_prediction=parsed,
                    )
                else:
                    print(f"Groq Vision API error ({res.status_code}): {res.text}")
        except Exception as exc:
            print(f"Groq Vision request failed: {exc}")
        return None

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
        raw_prediction: dict | None = None,
    ) -> tuple[str, dict]:
        affected = float(affected_area_pct or 0)
        
        # Check if AI returned structured severity/summary/actions
        ai_data = raw_prediction if isinstance(raw_prediction, dict) else {}
        severity = ai_data.get("severity")
        if not severity:
            if confidence >= 0.85 and affected >= 15:
                severity = "high"
            elif confidence >= 0.65 or affected >= 5:
                severity = "medium"
            else:
                severity = "low"

        actions = list(ai_data.get("actions", []))
        if not actions:
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

        summary = ai_data.get("summary") or f"{disease_label} detected with {confidence:.2%} confidence."

        return severity, {
            "summary": summary,
            "actions": actions,
            "yield_impact": yield_impact,
        }
