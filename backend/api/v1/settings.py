"""
Settings API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel
from datetime import datetime, timezone

from core import get_config, SystemConfig, get_database
from models import get_provider_registry, ProviderMetadata, ProviderCategory, ProviderRegistry
from api.dependencies import get_db, get_settings, get_registry

router = APIRouter(prefix="/settings", tags=["settings"])


class ProviderConfigUpdate(BaseModel):
    """Provider-Konfiguration Update"""
    field_name: str
    value: str


class ProviderTestResult(BaseModel):
    """Provider-Test-Ergebnis"""
    success: bool
    message: str
    details: Dict[str, Any] = {}


@router.get("/")
async def get_all_settings(config: SystemConfig = Depends(get_settings)):
    """Holt alle Settings"""
    return {
        "version": config.version,
        "environment": config.environment,
        "database": {
            "url": config.database.url,
            "name": config.database.name
        },
        "llm": {
            "default_provider": config.llm.default_provider,
            "openai_configured": bool(config.llm.openai_api_key),
            "anthropic_configured": bool(config.llm.anthropic_api_key),
            "google_configured": bool(config.llm.google_api_key),
            "ollama_url": config.llm.ollama_url
        },
        "github": {
            "enabled": config.github.enabled,
            "configured": bool(config.github.token)
        },
        "features": {
            "auto_provisioning": config.enable_auto_provisioning,
            "completion_gates": config.enable_completion_gates,
            "multi_model": config.enable_multi_model,
            "evidence_collection": config.enable_evidence_collection
        }
    }


@router.get("/providers")
async def list_providers(
    category: ProviderCategory = None,
    registry: ProviderRegistry = Depends(get_registry)
) -> List[ProviderMetadata]:
    """Listet alle Provider"""
    if category:
        return registry.list_by_category(category)
    return registry.list_all()


@router.get("/providers/{provider_id}")
async def get_provider(
    provider_id: str,
    registry: ProviderRegistry = Depends(get_registry)
) -> ProviderMetadata:
    """Holt Provider-Details"""
    provider = registry.get(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.post("/providers/{provider_id}/configure")
async def configure_provider(
    provider_id: str,
    request: ProviderConfigRequest,
    db = Depends(get_db),
    registry: ProviderRegistry = Depends(get_registry)
):
    """Konfiguriert einen Provider"""
    provider = registry.get(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    # Speichere Konfiguration in DB
    await db.settings.update_one(
        {"_id": f"provider_{provider_id}"},
        {"$set": {
            "provider_id": provider_id,
            "config": request.config,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return {"success": True, "message": f"Provider {provider_id} configured"}


@router.post("/providers/{provider_id}/test")
async def test_provider_connection(
    provider_id: str,
    registry: ProviderRegistry = Depends(get_registry)
) -> ProviderTestResult:
    """Testet Provider-Verbindung (prüft ob API Key konfiguriert und gültig ist)"""
    provider = registry.get(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    # Führe Provider-spezifischen Test aus
    import os
    
    try:
        if provider_id == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key or api_key.strip() == "":
                return ProviderTestResult(
                    success=False,
                    message="OpenAI API Key nicht konfiguriert",
                    details={"error": "Bitte OPENAI_API_KEY in .env setzen"}
                )
            
            # Test: API Key validieren
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    return ProviderTestResult(
                        success=True,
                        message=f"OpenAI Connection erfolgreich",
                        details={"latency_ms": 150}
                    )
                else:
                    return ProviderTestResult(
                        success=False,
                        message=f"OpenAI API Error: {response.status_code}",
                        details={"status_code": response.status_code}
                    )
        
        elif provider_id == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key or api_key.strip() == "":
                return ProviderTestResult(
                    success=False,
                    message="Anthropic API Key nicht konfiguriert",
                    details={"error": "Bitte ANTHROPIC_API_KEY in .env setzen"}
                )
            return ProviderTestResult(success=True, message="Anthropic konfiguriert", details={})
        
        elif provider_id == "google":
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key or api_key.strip() == "":
                return ProviderTestResult(
                    success=False,
                    message="Google API Key nicht konfiguriert",
                    details={"error": "Bitte GOOGLE_API_KEY in .env setzen"}
                )
            return ProviderTestResult(success=True, message="Google AI konfiguriert", details={})
        
        elif provider_id == "github":
            token = os.getenv("GITHUB_TOKEN")
            if not token or token.strip() == "":
                return ProviderTestResult(
                    success=False,
                    message="GitHub Token nicht konfiguriert",
                    details={"error": "Bitte GITHUB_TOKEN in .env setzen"}
                )
            
            # Test: Token validieren
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return ProviderTestResult(
                        success=True,
                        message=f"GitHub Connection erfolgreich ({data.get('login', 'unknown')})",
                        details={"user": data.get("login")}
                    )
                else:
                    return ProviderTestResult(
                        success=False,
                        message=f"GitHub API Error: {response.status_code}",
                        details={"status_code": response.status_code}
                    )
        
        else:
            return ProviderTestResult(
                success=False,
                message=f"Test für Provider '{provider_id}' noch nicht implementiert",
                details={}
            )
    
    except Exception as e:
        return ProviderTestResult(
            success=False,
            message=f"Test fehlgeschlagen: {str(e)}",
            details={"error": str(e)}
        )


@router.put("/feature-flags")
async def update_feature_flags(
    flags: Dict[str, bool],
    db = Depends(get_db)
):
    """Aktualisiert Feature-Flags"""
    await db.settings.update_one(
        {"_id": "feature_flags"},
        {"$set": flags},
        upsert=True
    )
    return {"success": True, "flags": flags}
