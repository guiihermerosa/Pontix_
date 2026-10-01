"""
Configurações da aplicação Pontix.
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
    APP_NAME: str = "Pontix"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    REQUIRE_AUTH: bool = os.getenv("REQUIRE_AUTH", "False").lower() == "true"
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: Optional[str] = os.getenv("SUPABASE_SERVICE_KEY")
    
    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Banco de dados local (SQLite)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/facial.db")
    
    # Sincronização
    SYNC_INTERVAL_MINUTES: int = int(os.getenv("SYNC_INTERVAL_MINUTES", "5"))
    SYNC_MAX_RETRIES: int = int(os.getenv("SYNC_MAX_RETRIES", "3"))
    SYNC_BATCH_SIZE: int = int(os.getenv("SYNC_BATCH_SIZE", "100"))
    
    # Email (Resend)
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM_EMAIL: str = os.getenv("RESEND_FROM_EMAIL", "no-reply@pontix.com")
    RESEND_FROM_NAME: str = os.getenv("RESEND_FROM_NAME", "Pontix")
    
    # Empresa padrão (para desenvolvimento)
    DEFAULT_COMPANY_NAME: str = os.getenv("DEFAULT_COMPANY_NAME", "Empresa Demo")
    DEFAULT_COMPANY_CNPJ: str = os.getenv("DEFAULT_COMPANY_CNPJ", "")
    
    # Segurança
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000")
    ALLOWED_HOSTS: str = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/pontix.log")
    LOG_MAX_SIZE_MB: int = int(os.getenv("LOG_MAX_SIZE_MB", "10"))
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    
    # URLs da aplicação
    APP_URL: str = os.getenv("APP_URL", "http://localhost:8000")
    WEB_APP_URL: str = os.getenv("WEB_APP_URL", "http://localhost:3000")
    
    # Storage (para uploads)
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    
    # Cache
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Instância global das configurações
settings = Settings()

# Função para obter configurações
def get_settings() -> Settings:
    return settings