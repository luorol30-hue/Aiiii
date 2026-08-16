# Production Cloud Deployment Guide

This guide details how to take the **Farm AI Intelligence Platform** live in production using **Vercel** (Next.js frontend) and **Render** / **Railway** (FastAPI backend + PostgreSQL & Redis).

---

## Architecture

```text
┌─────────────────────────────────────────────────────────┐
│               Users (Web & Mobile Browser)              │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│              Vercel Frontend (Next.js 15)               │
│            https://farm-ai.vercel.app                   │
└────────────────────────────┬────────────────────────────┘
                             │ REST API HTTPS
                             ▼
┌─────────────────────────────────────────────────────────┐
│            Render / Railway API (FastAPI)               │
│         https://farm-ai-api.onrender.com                │
└────────────┬───────────────┬───────────────┬────────────┘
             │               │               │
             ▼               ▼               ▼
┌──────────────────┐ ┌───────────────┐ ┌──────────────────┐
│ Cloud PostgreSQL │ │ Cloudflare R2 │ │  Upstash Redis   │
│ (Render / Neon)  │ │   / AWS S3    │ │  / Qdrant Cloud  │
└──────────────────┘ └───────────────┘ └──────────────────┘
```

---

## 1. Deploy Backend + Database to Render (1-Click Blueprint)

The repository includes `render.yaml` which automatically provisions the FastAPI service, PostgreSQL database, and Redis cache.

### Option A: Using Render Blueprints (Recommended)
1. Push this repository to **GitHub** or **GitLab**.
2. Log in to [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** > **Blueprint**.
4. Connect your repository. Render will automatically detect `render.yaml`.
5. Fill in the required secrets (or leave optional ones blank):
   - `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`
   - `OPENWEATHER_API_KEY`
6. Click **Apply**.
7. Render will automatically build the API, provision Postgres & Redis, and execute database initialization via `python -m app.db_init`.
8. Copy your live API URL (e.g. `https://farm-ai-api.onrender.com`).

### Option B: Manual Render Service Setup
If not using Blueprints:
1. **Create PostgreSQL**: Click **New +** > **PostgreSQL**. Set Name: `farm-ai-postgres`, Database: `farm_ai`. Copy the Internal Connection String.
2. **Create Redis**: Click **New +** > **Redis**. Copy the Internal Connection String.
3. **Create Web Service**: Click **New +** > **Web Service**.
   - **Root Directory**: `services/api`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Pre-Deploy Command**: `python -m app.db_init`
   - **Health Check Path**: `/api/v1/health`
4. Add all environment variables listed in the [Environment Variables Checklist](#production-environment-variables-checklist).

---

## 2. Deploy Frontend to Vercel

1. Log in to [Vercel](https://vercel.com).
2. Click **Add New...** > **Project** and select your GitHub repository.
3. In the project configuration:
   - **Framework Preset**: `Next.js`
   - **Root Directory**: Click `Edit` and choose `apps/web`.
4. Add Environment Variable:
   - `NEXT_PUBLIC_API_BASE_URL`: Your live backend API URL (e.g., `https://farm-ai-api.onrender.com` without trailing slash).
5. Click **Deploy**.
6. Once deployed, Vercel will assign a production domain (e.g. `https://farm-ai.vercel.app`).
7. Update `CORS_ORIGINS` in your Render backend settings to include your Vercel URL (e.g., `https://farm-ai.vercel.app`).

---

## 3. Alternative Backend Deployment: Railway

1. Install Railway CLI or connect via [railway.app](https://railway.app).
2. Create a new project and add:
   - **PostgreSQL Database**
   - **Redis Database**
   - **GitHub Repo Service** pointing to this repository (`railway.json` is preconfigured).
3. Set `NEXT_PUBLIC_API_BASE_URL` on Vercel to your Railway domain.

---

## 4. Cloud Object Storage Setup (Cloudflare R2 or AWS S3)

The platform requires S3-compatible storage for leaf disease photos and generated reports.

### Using Cloudflare R2 (Free Tier: 10 GB Storage & Zero Egress Fees)
1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/) > **R2 Object Storage**.
2. Create a bucket named `farm-ai`.
3. Go to **Manage R2 API Tokens** > **Create API Token** (Permissions: Object Read & Write).
4. Note the:
   - `S3_ENDPOINT_URL`: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`
   - `S3_ACCESS_KEY_ID`: Access Key ID
   - `S3_SECRET_ACCESS_KEY`: Secret Access Key
   - `S3_PUBLIC_BASE_URL`: Your custom domain or R2 public development URL.

---

## 5. Managed Vector Search (Qdrant Cloud)

1. Sign up for a free 1GB cluster at [Qdrant Cloud](https://cloud.qdrant.io/).
2. Create a cluster and copy the endpoint URL (e.g., `https://xxxxxx-xxxx.us-east4-0.gcp.cloud.qdrant.io:6333`).
3. Set `QDRANT_URL` in your backend environment variables.

---

## Production Environment Variables Checklist

### Backend Service (`services/api` / Render / Railway)

| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Environment mode | `production` |
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql+psycopg://user:pass@host:5432/farm_ai` |
| `REDIS_URL` | Redis connection URL | `redis://user:pass@host:6379/0` |
| `QDRANT_URL` | Qdrant vector database URL | `https://xxxx.qdrant.io:6333` |
| `JWT_SECRET` | Secret key for JWT signing | `64+ char random string` |
| `JWT_ALGORITHM` | Algorithm for JWT | `HS256` |
| `JWT_EXPIRES_MINUTES` | Access token lifespan | `10080` (7 days) |
| `CORS_ORIGINS` | Comma-separated allowed web origins | `https://farm-ai.vercel.app,http://localhost:3000` |
| `S3_BUCKET` | S3 / R2 Bucket name | `farm-ai` |
| `S3_REGION` | S3 Region | `us-east-1` or `auto` |
| `S3_ENDPOINT_URL` | Custom endpoint (if using R2/MinIO) | `https://<id>.r2.cloudflarestorage.com` |
| `S3_ACCESS_KEY_ID` | Storage access key | `your_access_key` |
| `S3_SECRET_ACCESS_KEY`| Storage secret key | `your_secret_key` |
| `S3_PUBLIC_BASE_URL` | Public image delivery URL | `https://pub-xxxx.r2.dev/farm-ai` |
| `WEATHER_PROVIDER` | Weather service provider | `openweather` or `weatherapi` |
| `OPENWEATHER_API_KEY`| OpenWeather API Key | `your_openweather_key` |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID (optional) | `xxxx.apps.googleusercontent.com` |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID (optional) | `ACxxxx` |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token (optional) | `your_token` |
| `TWILIO_VERIFY_SERVICE_SID` | Twilio Verify SID (optional) | `VAxxxx` |

### Frontend App (`apps/web` / Vercel)

| Variable | Description | Example |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_BASE_URL` | URL of the live backend API | `https://farm-ai-api.onrender.com` |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Google Maps API key (optional) | `AIzaSy...` |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | Mapbox token (optional) | `pk.eyJ...` |

---

## 6. Verification & Health Checks

Once deployed, verify everything is healthy:

1. **Backend Health Check**:
   ```bash
   curl https://farm-ai-api.onrender.com/api/v1/health
   # Expected response: {"status": "ok"}
   ```

2. **Frontend Connectivity**:
   Open `https://farm-ai.vercel.app` in your browser. Register a test farmer account or log in to confirm seamless API communication.
