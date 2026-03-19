from typing import Optional
from pydantic import BaseModel, EmailStr

class SignupRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class SettingsResponse(BaseModel):
    base_currency: str
    tracked_currencies: str
    tracked_metals: str
    thresholds_json: str
    api_usage_count: int
    api_usage_month: str

class SettingsUpdate(BaseModel):
    base_currency: Optional[str] = None
    tracked_currencies: Optional[str] = None
    tracked_metals: Optional[str] = None
    thresholds_json: Optional[str] = None
