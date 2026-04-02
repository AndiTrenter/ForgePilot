"""
API Dependencies
FastAPI Dependency Injection
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core import get_database, get_config, Database, SystemConfig
from models import get_provider_registry, ProviderRegistry

# Security
security = HTTPBearer(auto_error=False)


async def get_db() -> Database:
    """Dependency: Database"""
    return get_database()


def get_settings() -> SystemConfig:
    """Dependency: Settings"""
    return get_config()


def get_registry() -> ProviderRegistry:
    """Dependency: Provider Registry"""
    return get_provider_registry()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """Dependency: Current User (für zukünftige Auth)"""
    # TODO: Implement proper authentication
    # Für jetzt: kein Auth erforderlich (Development)
    return {"id": "system", "role": "admin"}
