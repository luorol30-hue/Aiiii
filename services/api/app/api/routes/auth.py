from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import ExternalServiceNotConfigured, service_not_configured, service_unavailable
from app.db import get_db
from app.models import User
from app.schemas import (
    GoogleLoginRequest,
    LoginRequest,
    PhoneOtpSendRequest,
    PhoneOtpVerifyRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user, settings))


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user, settings))


@router.post("/google", response_model=TokenResponse)
def google_login(
    payload: GoogleLoginRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    if not settings.google_client_id:
        raise service_not_configured("GOOGLE_CLIENT_ID is not configured")
    try:
        claims = id_token.verify_oauth2_token(
            payload.id_token,
            google_requests.Request(),
            settings.google_client_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token") from exc

    email = claims.get("email")
    google_subject = claims.get("sub")
    if not email or not google_subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google token missing identity")

    user = db.scalar(
        select(User).where(or_(User.google_subject == google_subject, User.email == email.lower()))
    )
    if not user:
        user = User(
            email=email.lower(),
            google_subject=google_subject,
            full_name=claims.get("name") or email,
        )
        db.add(user)
    else:
        user.google_subject = user.google_subject or google_subject
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user, settings))


@router.post("/phone/send-otp")
def send_phone_otp(
    payload: PhoneOtpSendRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    try:
        client, service_sid = _twilio_verify(settings)
        client.verify.v2.services(service_sid).verifications.create(to=payload.phone, channel="sms")
    except ExternalServiceNotConfigured as exc:
        raise service_not_configured(str(exc)) from exc
    except Exception as exc:
        raise service_unavailable("Twilio Verify request failed") from exc
    return {"status": "sent"}


@router.post("/phone/verify-otp", response_model=TokenResponse)
def verify_phone_otp(
    payload: PhoneOtpVerifyRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    try:
        client, service_sid = _twilio_verify(settings)
        check = client.verify.v2.services(service_sid).verification_checks.create(
            to=payload.phone,
            code=payload.code,
        )
    except ExternalServiceNotConfigured as exc:
        raise service_not_configured(str(exc)) from exc
    except Exception as exc:
        raise service_unavailable("Twilio Verify request failed") from exc

    if check.status != "approved":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP")

    user = db.scalar(select(User).where(User.phone == payload.phone))
    if not user:
        user = User(phone=payload.phone, full_name=payload.full_name or payload.phone)
        db.add(user)
        db.commit()
        db.refresh(user)
    return TokenResponse(access_token=create_access_token(user, settings))


@router.get("/me", response_model=UserOut)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


def _twilio_verify(settings: Settings):
    if (
        not settings.twilio_account_sid
        or not settings.twilio_auth_token
        or not settings.twilio_verify_service_sid
    ):
        raise ExternalServiceNotConfigured("Twilio Verify credentials are not configured")
    from twilio.rest import Client

    return Client(settings.twilio_account_sid, settings.twilio_auth_token), settings.twilio_verify_service_sid
