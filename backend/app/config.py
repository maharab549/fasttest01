from typing import Any, List

from pydantic import field_validator
from pydantic_settings import BaseSettings
import json


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./marketplace.db"
    # Optional: Supabase/Postgres external database URL. If set and use_supabase=True,
    # the app will connect to this instead of the local SQLite database.
    supabase_database_url: str | None = None
    use_supabase: bool = False
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # JWT
    secret_key: str = "development-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Stripe
    stripe_publishable_key: str = "pk_test_default"
    stripe_secret_key: str = "sk_test_default"

    # AI
    gemini_api_key: str = "default-gemini-key"
    groq_api_key: str | None = None
    
    # CORS
    cors_origins: List[str] = []

    def __init__(self, **data):
        super().__init__(**data)
        if isinstance(self.cors_origins, str):
            self.cors_origins = json.loads(self.cors_origins)
    
    # App
    debug: bool = True
    # Base URL used to build absolute image URLs in API responses (adjust for production)
    api_base_url: str = "http://localhost:8000"

    @field_validator("debug", "use_supabase", mode="before")
    @classmethod
    def parse_flexible_bool(cls, value: Any) -> Any:
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "y", "on", "debug", "development", "dev"}:
                return True
            if normalized in {"0", "false", "no", "n", "off", "release", "production", "prod"}:
                return False
        return value
    
    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
