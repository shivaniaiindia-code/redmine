from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_FILE = BACKEND_DIR / "company_intel.db"
DEFAULT_DATABASE_URL = f"sqlite+aiosqlite:///{DEFAULT_DB_FILE.as_posix()}"

class Settings(BaseSettings):
    PROJECT_NAME: str = "Company Intelligence Platform"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Security & JWT
    SECRET_KEY: str = "cip-super-secret-production-key-change-in-env-2026-xyz"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
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
    DEFAULT_ALERT_EMAIL: str = "anil.aiindia@gmail.com"
    DEFAULT_ALERT_NAME: str = "Anil (Administrator)"
    
    # Redmine Integration
    REDMINE_URL: str = ""
    REDMINE_API_KEY: str = ""
    REDMINE_SYNC_INTERVAL_MINUTES: int = 5
    
    # Google Chat Integration (Mandatory Admin Mirroring)
    GOOGLE_CHAT_ADMIN_WEBHOOK_URL: str = ""
    
    # OpenRouter AI
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_DEFAULT_MODEL: str = "qwen/qwen3.5-flash-02-23"
    OPENROUTER_FALLBACK_MODEL: str = "qwen/qwen3.8-flash"
    
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

