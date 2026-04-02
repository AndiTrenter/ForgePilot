"""
Core Configuration Management
Zentrale Konfiguration für das gesamte System
"""
import os
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseModel):
    """Datenbank-Konfiguration"""
    url: str = Field(default_factory=lambda: os.environ.get('MONGO_URL', 'mongodb://mongodb:27017'))
    name: str = Field(default_factory=lambda: os.environ.get('DB_NAME', 'forgepilot'))
    max_pool_size: int = 10
    min_pool_size: int = 1


class LLMConfig(BaseModel):
    """LLM Provider Konfiguration"""
    default_provider: str = "openai"
    openai_api_key: Optional[str] = Field(default_factory=lambda: os.environ.get('OPENAI_API_KEY'))
    anthropic_api_key: Optional[str] = Field(default_factory=lambda: os.environ.get('ANTHROPIC_API_KEY'))
    google_api_key: Optional[str] = Field(default_factory=lambda: os.environ.get('GOOGLE_API_KEY'))
    ollama_url: str = Field(default_factory=lambda: os.environ.get('OLLAMA_URL', 'http://localhost:11434'))


class GitHubConfig(BaseModel):
    """GitHub Integration Konfiguration"""
    token: Optional[str] = Field(default_factory=lambda: os.environ.get('GITHUB_TOKEN'))
    enabled: bool = Field(default_factory=lambda: bool(os.environ.get('GITHUB_TOKEN')))


class SecurityConfig(BaseModel):
    """Sicherheits-Konfiguration"""
    secret_key: str = Field(default_factory=lambda: os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'))
    allowed_origins: list[str] = Field(default_factory=lambda: os.environ.get('ALLOWED_ORIGINS', '*').split(','))
    max_upload_size: int = 100 * 1024 * 1024  # 100MB


class SystemConfig(BaseSettings):
    """Haupt-System-Konfiguration"""
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"  # Ignoriere unbekannte ENV-Variablen
    }
    
    # Version
    version: str = Field(default_factory=lambda: os.environ.get('APP_VERSION', '2.9.0'))
    environment: str = Field(default_factory=lambda: os.environ.get('ENVIRONMENT', 'development'))
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8001
    reload: bool = Field(default_factory=lambda: os.environ.get('ENVIRONMENT', 'development') == 'development')
    
    # Paths
    workspaces_dir: str = "/app/workspaces"
    templates_dir: str = "/app/backend/provisioning/templates"
    
    # Sub-Configs
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    # Feature Flags
    enable_auto_provisioning: bool = True
    enable_completion_gates: bool = True
    enable_multi_model: bool = False  # Wird in Etappe 5 aktiviert
    enable_evidence_collection: bool = True


# Singleton Instance
_config: Optional[SystemConfig] = None


def get_config() -> SystemConfig:
    """Gibt die globale Config-Instanz zurück"""
    global _config
    if _config is None:
        _config = SystemConfig()
    return _config


def reload_config():
    """Lädt die Konfiguration neu"""
    global _config
    _config = SystemConfig()
    return _config
