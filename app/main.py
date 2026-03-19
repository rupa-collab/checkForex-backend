from datetime import datetime, timedelta, timezone
import secrets
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.db import get_session, init_db
from app.models import User, VerificationToken, UserSettings
from app.schemas import SignupRequest, LoginRequest, TokenResponse, SettingsResponse, SettingsUpdate
from app.security import hash_password, verify_password, create_access_token
from app.email import send_verification_email
from app.settings import settings

app = FastAPI(title="Check Forex Rate Backend")

# CORS for Android app (use specific origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.on_event("startup")
def on_startup():
    init_db()


def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    try:
        payload = __import__("jose").jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        email = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@app.post("/auth/signup")
def signup(payload: SignupRequest, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    session.add(user)
    session.commit()
    session.refresh(user)

    token = secrets.token_urlsafe(32)
    verify = VerificationToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
    )
    session.add(verify)
    session.commit()

    verify_url = f"{settings.APP_BASE_URL}/auth/verify?token={token}"
    send_verification_email(payload.email, verify_url)

    return {"message": "Signup successful. Please verify your email."}


@app.get("/auth/verify")
def verify_email(token: str, session: Session = Depends(get_session)):
    record = session.exec(select(VerificationToken).where(VerificationToken.token == token)).first()
    if not record:
        raise HTTPException(status_code=400, detail="Invalid token")
    if record.used_at is not None:
        return {"message": "Email already verified"}
    if record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expired")

    user = session.get(User, record.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    user.is_verified = True
    user.updated_at = datetime.now(timezone.utc)
    record.used_at = datetime.now(timezone.utc)
    session.add(user)
    session.add(record)
    session.commit()

    settings_row = session.exec(select(UserSettings).where(UserSettings.user_id == user.id)).first()
    if not settings_row:
        settings_row = UserSettings(user_id=user.id)
        session.add(settings_row)
        session.commit()

    return {"message": "Email verified"}


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == payload.email)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    token = create_access_token(user.email)
    return TokenResponse(access_token=token)


@app.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"email": user.email, "is_verified": user.is_verified}


@app.get("/settings", response_model=SettingsResponse)
def get_settings(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    settings_row = session.exec(select(UserSettings).where(UserSettings.user_id == user.id)).first()
    if not settings_row:
        settings_row = UserSettings(user_id=user.id)
        session.add(settings_row)
        session.commit()
        session.refresh(settings_row)
    return SettingsResponse(
        base_currency=settings_row.base_currency,
        tracked_currencies=settings_row.tracked_currencies,
        tracked_metals=settings_row.tracked_metals,
        thresholds_json=settings_row.thresholds_json,
        api_usage_count=settings_row.api_usage_count,
        api_usage_month=settings_row.api_usage_month,
    )


@app.put("/settings", response_model=SettingsResponse)
def update_settings(update: SettingsUpdate, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    settings_row = session.exec(select(UserSettings).where(UserSettings.user_id == user.id)).first()
    if not settings_row:
        settings_row = UserSettings(user_id=user.id)

    if update.base_currency is not None:
        settings_row.base_currency = update.base_currency
    if update.tracked_currencies is not None:
        settings_row.tracked_currencies = update.tracked_currencies
    if update.tracked_metals is not None:
        settings_row.tracked_metals = update.tracked_metals
    if update.thresholds_json is not None:
        settings_row.thresholds_json = update.thresholds_json

    session.add(settings_row)
    session.commit()
    session.refresh(settings_row)

    return SettingsResponse(
        base_currency=settings_row.base_currency,
        tracked_currencies=settings_row.tracked_currencies,
        tracked_metals=settings_row.tracked_metals,
        thresholds_json=settings_row.thresholds_json,
        api_usage_count=settings_row.api_usage_count,
        api_usage_month=settings_row.api_usage_month,
    )
