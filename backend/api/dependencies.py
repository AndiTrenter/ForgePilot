"""
API Dependencies
FastAPI Dependency Injection
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import sys
from pathlib import Path

# Add parent dir to path to import from core/models
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from core.config import get_config, SystemConfig
    from models.provider import get_provider_registry, ProviderRegistry
except ImportError as e:
    # Fallback wenn Module nicht verfügbar
    print(f"Warning: Could not import modules: {e}")
    SystemConfig = None
    ProviderRegistry = None

# Security
security = HTTPBearer(auto_error=False)


async def get_db():
    """Dependency: Database - returns mongo db instance from server.py"""
    # Import here to avoid circular dependency
    import server
    return server.db


def get_settings():
    """Dependency: Settings"""
    if get_config:
        return get_config()
    # Fallback
    return None


def get_registry():
    """Dependency: Provider Registry"""
    if get_provider_registry:
        return get_provider_registry()
    # Fallback
    return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """Dependency: Current User (für zukünftige Auth)"""
    # TODO: Implement proper authentication
    # Für jetzt: kein Auth erforderlich (Development)
    return {"id": "system", "role": "admin"}
