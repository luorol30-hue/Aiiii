# AI Farm Intelligence Platform

Production-oriented starter for a farmer-facing web/mobile backend:

- Next.js frontend in `apps/web`
- FastAPI REST API in `services/api`
- PostgreSQL, Redis, Qdrant, and S3-compatible object storage via Docker Compose
- Real integrations only. No seed data, mocked API responses, or fake model predictions are included.

## What Is Implemented

- JWT auth with password login, Google ID token login, and Twilio Verify phone OTP hooks
- Farm, field, crop, report, notification, and AI prediction tables
- Leaf image workflow: upload to S3/R2/MinIO, run a YOLO-family model, measure affected area with OpenCV, fetch weather, read soil data, optionally run yield impact model, save results, and publish a notification when action is needed
- Weather provider abstraction for OpenWeather, Tomorrow.io, or WeatherAPI
- Satellite data hooks for NASA POWER and Sentinel Hub
- Frontend account flow, farm creation, image upload, dashboard, reports, and notifications wired to the FastAPI service

## No Mock Data Policy

The app does not invent weather, diseases, farms, prices, users, or model output.

If a required credential, model file, database, or external service is missing, the API returns a clear error instead of pretending success. For local development, MinIO is used as real S3-compatible object storage.

## Repository Layout

```text
apps/web          Next.js frontend
services/api      FastAPI backend
infra             SQL migration and deployment notes
docker-compose.yml
render.yaml       Render 1-click cloud blueprint
DEPLOYMENT.md     Production deployment guide
.env.example
```

## Cloud Production Deployment (Vercel + Render / Railway)

See [DEPLOYMENT.md](file:///c:/xampp/htdocs/aiiii/DEPLOYMENT.md) for full step-by-step instructions on deploying the Next.js frontend to **Vercel** and the FastAPI backend, PostgreSQL database, and Redis cache to **Render** or **Railway**.


## Local Setup

1. Copy `.env.example` to `.env` and fill in real credentials.
2. Put trained model artifacts on disk and set:
   - `DISEASE_MODEL_PATH`
   - `YIELD_MODEL_PATH` if yield impact predictions are enabled
3. Start infrastructure:

```bash
docker compose up postgres redis qdrant minio
```

4. Apply the database schema:

```bash
psql "postgresql://postgres:postgres@localhost:5432/farm_ai" -f infra/postgres/001_initial_schema.sql
```

5. Start the API:

```bash
cd services/api
uvicorn app.main:app --reload --port 8000
```

6. Start the frontend:

```bash
cd apps/web
npm install
npm run dev
```

Open `http://localhost:3000`.

## Required Production Services

- PostgreSQL
- Redis
- Qdrant
- AWS S3, Cloudflare R2, Supabase Storage adapter, or MinIO
- OpenWeather, Tomorrow.io, or WeatherAPI
- Google OAuth client
- Twilio Verify for phone OTP and SMS notifications
- Firebase Cloud Messaging for push notifications
- SMTP provider for email notifications
- Trained YOLO/RT-DETR/SAM2/PyTorch model artifacts

## API Surface

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/google`
- `POST /api/v1/auth/phone/send-otp`
- `POST /api/v1/auth/phone/verify-otp`
- `GET /api/v1/farms`
- `POST /api/v1/farms`
- `GET /api/v1/crops`
- `POST /api/v1/crops`
- `POST /api/v1/ai/disease-detections`
- `GET /api/v1/weather/forecast`
- `GET /api/v1/satellite/nasa-power/daily`
- `POST /api/v1/satellite/sentinel/search`
- `GET /api/v1/reports`
- `GET /api/v1/notifications`

## Training Data

This repository expects trained artifacts rather than bundled datasets. Suitable training sources include PlantVillage, PlantDoc, Rice Leaf Disease, and Cassava Leaf Disease datasets. Store dataset licenses and provenance separately before training models for production use.
