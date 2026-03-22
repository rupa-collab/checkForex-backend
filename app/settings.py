from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_EXPIRES_MINUTES: int = 60
    SENDGRID_API_KEY: str
    SENDGRID_FROM: str
    APP_BASE_URL: str = "http://checkForex-backend.onrender.com"
    DEV_OTP_MODE: bool = True
    class Config:
        env_file = ".env"

settings = Settings()
