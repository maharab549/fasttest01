from pydantic_settings import BaseSettings
from typing import List
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
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Stripe
    stripe_publishable_key: str
    stripe_secret_key: str

    # AI
    gemini_api_key: str
    groq_api_key: str | None = None
    
    # CORS
    cors_origins: List[str] = []

    def __init__(self, **data):
        super().__init__(**data)
        if isinstance(self.cors_origins, str):
            self.cors_origins = json.loads(self.cors_origins)
    
    # App
    debug: bool = True
    
    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()

