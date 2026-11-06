from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_FILE = BACKEND_DIR / "company_intel.db"
DEFAULT_DATABASE_URL = f"sqlite+aiosqlite:///{DEFAULT_DB_FILE.as_posix()}"

# The built-in root Super Admin account (protected: cannot be blocked, deleted or demoted)
ROOT_ADMIN_EMAIL = "admin@aiindia.com"

# Signing keys that were ever committed to this repository: anyone could forge tokens with them
INSECURE_SECRET_KEYS = {"cip-super-secret-production-key-change-in-env-2026-xyz", "change-me", "secret"}

class Settings(BaseSettings):
    PROJECT_NAME: str = "Project Manager"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Security & JWT — SECRET_KEY must come from backend/.env (never a value committed to the repo)
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Password of the root admin account (admin@aiindia.com), applied on every startup. Empty = password login disabled
    ADMIN_PASSWORD: str = ""

    @field_validator("SECRET_KEY", mode="after")
    @classmethod
    def require_strong_secret(cls, v: str) -> str:
        if not v or len(v) < 32 or v in INSECURE_SECRET_KEYS:
            raise ValueError(
                "SECRET_KEY in backend/.env is missing, too short or a published default. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        return v

    # Database: Anchored to backend/company_intel.db
    DATABASE_URL: str = DEFAULT_DATABASE_URL

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def anchor_database_url(cls, v: str) -> str:
        # If relative SQLite path, anchor to backend directory
        if v.startswith("sqlite+aiosqlite:///./") or v == "sqlite+aiosqlite:///company_intel.db":
            return DEFAULT_DATABASE_URL
        return v
    
    # Default Alert Recipient (configurable from Admin Settings)
    # All system-generated alerts (employee, project, task, team, company) route here.
    DEFAULT_ALERT_EMAIL: str = "connect.aiindia@gmail.com"
    DEFAULT_ALERT_NAME: str = "Administrator"
    
    # Redmine Integration
    REDMINE_URL: str = ""
    REDMINE_API_KEY: str = ""
    REDMINE_SYNC_INTERVAL_MINUTES: float = 1.0   # polling interval; a full sync takes ~6 s
    
    # SMTP Email Alerting (URGENT & CRITICAL alerts are delivered by email only)
    # Gmail: smtp.gmail.com:587 + STARTTLS, SMTP_PASSWORD = 16-char App Password.
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""          # Defaults to SMTP_USERNAME when blank
    SMTP_FROM_NAME: str = "Project Manager"
    SMTP_USE_STARTTLS: bool = True
    SMTP_USE_SSL: bool = False         # Implicit TLS (port 465); mutually exclusive with STARTTLS
    SMTP_TIMEOUT_SECONDS: float = 20.0
    # Severities that trigger an email (comma separated)
    EMAIL_ALERT_SEVERITIES: str = "URGENT,CRITICAL"

    # LLM-written alert emails (OpenRouter). Falls back to a structured template on any failure.
    EMAIL_AI_COMPOSE: bool = True
    EMAIL_AI_TIMEOUT_SECONDS: float = 25.0

    # AI assistant: LLM explains deterministic tool answers (number-guarded; falls back to the raw tool answer)
    AI_EXPLAIN_TOOL_ANSWERS: bool = True

    # Public dashboard URL used for deep links inside alert emails
    APP_BASE_URL: str = "http://localhost:3000"

    # Local time zone for the daily digest / weekly report schedule
    APP_TIMEZONE: str = "Asia/Kolkata"

    # OpenRouter AI
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_DEFAULT_MODEL: str = "nvidia/nemotron-3.5-super-vl:free"   # free, ~3 s
    OPENROUTER_FALLBACK_MODEL: str = "nvidia/nemotron-3.5-lightning:free"  # free fallback

    # Google OAuth 2.0
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000"
    ]
    
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

