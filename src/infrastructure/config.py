"""Environment & Node Configuration using Pydantic Settings.

Clean Architecture layer: Infrastructure.
Reads environment variables for database, Redis, Razorpay, and merchant profiles.
"""
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
    APP_NAME: str = "Universal Agentic Commerce Node"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    PUBLIC_BASE_URL: str = "https://agentic-commerce-node.onrender.com"

    # Active Merchant Setting
    ACTIVE_MERCHANT_ID: str = "dominos_in"

    # Database Settings (Neon PostgreSQL / Local SQLite fallback)
    DATABASE_URL: str = "sqlite:///./agentic_commerce.db"

    # Redis Gatekeeper Settings (Upstash Redis)
    REDIS_URL: Optional[str] = None
    UPSTASH_REDIS_REST_URL: Optional[str] = None
    UPSTASH_REDIS_REST_TOKEN: Optional[str] = None

    # Razorpay Payment Rails Settings
    RAZORPAY_KEY_ID: str = "rzp_test_placeholder_key"
    RAZORPAY_KEY_SECRET: str = "rzp_test_placeholder_secret"
    RAZORPAY_SANDBOX_MODE: bool = True

    # Quote Expiration Setting (Minutes)
    QUOTE_VALIDITY_MINUTES: int = 15


# Global singleton settings instance
settings = AppSettings()
