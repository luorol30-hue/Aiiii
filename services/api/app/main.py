from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import ExternalServiceNotConfigured, ExternalServiceUnavailable

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-initialize database tables on startup
    try:
        from app.db_init import init_database
        init_database()
    except Exception as exc:
        print(f"Warning: database schema initialization error: {exc}")
    yield


app = FastAPI(
    title="Farm AI API",
    version="0.1.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$|^http:\/\/localhost(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root_health():
    return {"status": "ok", "service": "farm-ai-api"}


@app.get("/health")
def base_health():
    return {"status": "ok"}


@app.exception_handler(ExternalServiceNotConfigured)
async def not_configured_handler(_: Request, exc: ExternalServiceNotConfigured):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(ExternalServiceUnavailable)
async def unavailable_handler(_: Request, exc: ExternalServiceUnavailable):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


app.include_router(api_router)
