"""
Configurações da aplicação Pontix Cloud.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()


class Settings(BaseSettings):
    """Configurações da aplicação."""
    
    # FastAPI
    APP_NAME: str = "Pontix Cloud"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    REQUIRE_AUTH: bool = os.getenv("REQUIRE_AUTH", "True").lower() == "true"
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: Optional[str] = os.getenv("SUPABASE_SERVICE_KEY")
    
    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Sincronização com sistema local
    LOCAL_SYSTEM_URL: str = os.getenv("LOCAL_SYSTEM_URL", "http://localhost:8000")
    LOCAL_SYSTEM_API_KEY: str = os.getenv("LOCAL_SYSTEM_API_KEY", "")
    
    # Email (Resend)
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM_EMAIL: str = os.getenv("RESEND_FROM_EMAIL", "noreply@pontix.com")
    RESEND_FROM_NAME: str = os.getenv("RESEND_FROM_NAME", "Pontix Cloud")
    
    # Segurança
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    ALLOWED_HOSTS: str = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/pontix-cloud.log")
    LOG_MAX_SIZE_MB: int = int(os.getenv("LOG_MAX_SIZE_MB", "10"))
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    
    # URLs da aplicação
    APP_URL: str = os.getenv("APP_URL", "http://localhost:8000")
    WEB_APP_URL: str = os.getenv("WEB_APP_URL", "http://localhost:3000")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Instância global das configurações
settings = Settings()


def get_settings() -> Settings:
    return settings
