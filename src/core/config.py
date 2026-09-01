"""Environment & Node Configuration using Pydantic Settings."""
import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server Settings
    APP_NAME: str = "Payvlo Universal Agentic Commerce Node"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    PUBLIC_BASE_URL: str = os.getenv(
        "PUBLIC_BASE_URL",
        os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000"),
    )

    # Security / JWT Settings
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY", "payvlo_super_secret_jwt_signing_key_2026"
    )

    # Active Merchant Setting
    ACTIVE_MERCHANT_ID: str = "dominos_in"

    # Database Settings (Neon PostgreSQL / Local SQLite fallback)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite:///./agentic_commerce.db"
    )

    # Redis Gatekeeper Settings (Upstash Redis)
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    UPSTASH_REDIS_REST_URL: Optional[str] = os.getenv("UPSTASH_REDIS_REST_URL")
    UPSTASH_REDIS_REST_TOKEN: Optional[str] = os.getenv("UPSTASH_REDIS_REST_TOKEN")

    # Razorpay Payment Rails Settings
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_placeholder_key")
    RAZORPAY_KEY_SECRET: str = os.getenv(
        "RAZORPAY_KEY_SECRET", "rzp_test_placeholder_secret"
    )
    RAZORPAY_SANDBOX_MODE: bool = True

    # Quote Expiration Setting (Minutes)
    QUOTE_VALIDITY_MINUTES: int = 15


# Global singleton settings instance
settings = AppSettings()
