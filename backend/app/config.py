from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./marketplace.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # JWT
    secret_key: str = "demo-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Stripe
    stripe_publishable_key: str = "pk_test_demo"
    stripe_secret_key: str = "sk_test_demo"
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
    
    # App
    debug: bool = True
    
    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()

