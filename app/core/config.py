"""
Application configuration using pydantic-settings
"""
from typing import List, Optional
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "D2C Analytics Platform"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str
    API_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str
    REDIS_SESSION_DB: int = 1
    REDIS_CACHE_DB: int = 2
    REDIS_RATE_LIMIT_DB: int = 3

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Encryption
    ENCRYPTION_KEY: str

    # Email
    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    SMTP_FROM_NAME: str

    # AWS S3
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "ap-south-1"
    AWS_S3_BUCKET: str

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # Razorpay
    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str
    RAZORPAY_WEBHOOK_SECRET: str

    # Sentry
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: str = "development"

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_API: str = "60/minute"
    RATE_LIMIT_REPORTS: str = "10/hour"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True

    # Shopify
    SHOPIFY_API_KEY: Optional[str] = None
    SHOPIFY_API_SECRET: Optional[str] = None
    SHOPIFY_API_VERSION: str = "2023-10"

    # Amazon SP-API
    AMAZON_CLIENT_ID: Optional[str] = None
    AMAZON_CLIENT_SECRET: Optional[str] = None
    AMAZON_REFRESH_TOKEN: Optional[str] = None
    AMAZON_REGION: str = "IN"

    # Flipkart
    FLIPKART_APP_ID: Optional[str] = None
    FLIPKART_APP_SECRET: Optional[str] = None

    # Shiprocket
    SHIPROCKET_EMAIL: Optional[str] = None
    SHIPROCKET_PASSWORD: Optional[str] = None

    # Facebook Ads
    FACEBOOK_APP_ID: Optional[str] = None
    FACEBOOK_APP_SECRET: Optional[str] = None
    FACEBOOK_ACCESS_TOKEN: Optional[str] = None

    # Google Ads
    GOOGLE_ADS_CLIENT_ID: Optional[str] = None
    GOOGLE_ADS_CLIENT_SECRET: Optional[str] = None
    GOOGLE_ADS_DEVELOPER_TOKEN: Optional[str] = None
    GOOGLE_ADS_REFRESH_TOKEN: Optional[str] = None

    # ML Models
    ML_MODELS_PATH: str = "./ml_models"
    ML_MODEL_RETRAIN_SCHEDULE: str = "0 2 * * 0"
    RTO_MODEL_MIN_SAMPLES: int = 1000
    DEMAND_FORECAST_MIN_HISTORY_DAYS: int = 180

    # Subscription Plans
    TRIAL_ORDER_LIMIT: int = 50
    STARTER_ORDER_LIMIT: int = 500
    GROWTH_ORDER_LIMIT: int = 2000
    PROFESSIONAL_ORDER_LIMIT: int = 999999

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


# Global settings instance
settings = Settings()
