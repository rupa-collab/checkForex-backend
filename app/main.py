from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import delete
from sqlmodel import Session, select

from app.db import get_session, init_db
from app.models import User, VerificationToken, UserSettings, OtpCode
from app.schemas import SignupRequest, LoginRequest, TokenResponse, SettingsResponse, SettingsUpdate, RequestOtp, VerifyOtp
from app.security import hash_password, verify_password, create_access_token
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



def hash_otp(email: str, otp: str) -> str:
    raw = (settings.JWT_SECRET + email.lower().strip() + otp).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def generate_otp() -> str:
    return f"{secrets.randbelow(1000000):06d}"\r\ndef get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
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



@app.post("/auth/request-otp")
def request_otp(payload: RequestOtp, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    session.exec(delete(OtpCode).where(OtpCode.email == payload.email))

    otp = generate_otp()
    record = OtpCode(
        email=payload.email,
        otp_hash=hash_otp(payload.email, otp),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
    )
    session.add(record)
    session.commit()

    # Local/dev mode: return OTP in response
    return {"message": "OTP generated", "otp": otp}


@app.post("/auth/verify-otp", response_model=TokenResponse)
def verify_otp(payload: VerifyOtp, session: Session = Depends(get_session)):
    record = session.exec(select(OtpCode).where(OtpCode.email == payload.email)).first()
    if not record:
        raise HTTPException(status_code=400, detail="OTP not found")
    if record.used_at is not None:
        raise HTTPException(status_code=400, detail="OTP already used")
    if record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="OTP expired")

    if record.otp_hash != hash_otp(payload.email, payload.otp):
        record.attempts += 1
        session.add(record)
        session.commit()
        raise HTTPException(status_code=400, detail="Invalid OTP")

    user = User(email=payload.email, password_hash=hash_password(payload.password), is_verified=True)
    session.add(user)
    record.used_at = datetime.now(timezone.utc)
    session.add(record)
    session.commit()

    token = create_access_token(user.email)
    return TokenResponse(access_token=token)\r\n\r\n@app.post("/auth/signup")
def signup(payload: SignupRequest, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=payload.email, password_hash=hash_password(payload.password), is_verified=True)
    session.add(user)
    session.commit()
    session.refresh(user)

    return {"message": "Signup successful."}


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
