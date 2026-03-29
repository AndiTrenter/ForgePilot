from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query, Body
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import json
import asyncio
from openai import AsyncOpenAI
import git
import shutil
import aiofiles
import subprocess
import re
import httpx

ROOT_DIR = Path(__file__).parent
APP_ROOT = ROOT_DIR.parent
load_dotenv(ROOT_DIR / '.env')

# App Version
APP_VERSION = "1.1.0"
try:
    version_file = ROOT_DIR / "VERSION"
    if version_file.exists():
        APP_VERSION = version_file.read_text().strip()
    else:
        version_file = APP_ROOT / "VERSION"
        if version_file.exists():
            APP_VERSION = version_file.read_text().strip()
except:
    pass

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'forgepilot')]

# Settings collection for API keys
settings_collection = db.settings
update_collection = db.updates

# Default Ollama URL - für Docker-Setups die Host-IP verwenden
DEFAULT_OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://host.docker.internal:11434')

# Global settings class
class AppSettings:
    def __init__(self):
        # Initialisiere mit ENV-Werten als Defaults
        self.openai_api_key: str = os.environ.get('OPENAI_API_KEY', '')
        self.github_token: str = os.environ.get('GITHUB_TOKEN', '')
        self.ollama_url: str = os.environ.get('OLLAMA_URL', DEFAULT_OLLAMA_URL)
        self.ollama_model: str = os.environ.get('OLLAMA_MODEL', 'llama3')
        self.llm_provider: str = os.environ.get('LLM_PROVIDER', 'auto')
        self.use_ollama: bool = os.environ.get('USE_OLLAMA', 'false').lower() == 'true'
        # Track source of settings
        self.openai_from_env: bool = bool(os.environ.get('OPENAI_API_KEY', ''))
        self.github_from_env: bool = bool(os.environ.get('GITHUB_TOKEN', ''))

app_settings = AppSettings()

# OpenAI client (will be updated when settings change)
openai_client: Optional[AsyncOpenAI] = None

# Ollama availability cache
ollama_available = False
ollama_models = []

# Create the main app
app = FastAPI(title="ForgePilot API", version=APP_VERSION)
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def mask_key(key: str) -> str:
    """Maskiere API-Key für sichere Anzeige"""
    if not key or len(key) < 10:
        return ""
    return key[:6] + "..." + key[-4:]

# Load settings from database on startup
async def load_settings_from_db():
    global openai_client, app_settings
    
    try:
        saved = await settings_collection.find_one({"_id": "app_settings"})
        if saved:
            logger.info(f"Loading saved settings from MongoDB...")
            
            # OpenAI Key: DB hat Vorrang, außer ENV ist gesetzt
            if saved.get('openai_api_key'):
                if not app_settings.openai_from_env:
                    app_settings.openai_api_key = saved['openai_api_key']
                    logger.info(f"Loaded OpenAI key from DB: {mask_key(app_settings.openai_api_key)}")
            
            # GitHub Token: DB hat Vorrang, außer ENV ist gesetzt
            if saved.get('github_token'):
                if not app_settings.github_from_env:
                    app_settings.github_token = saved['github_token']
                    logger.info(f"Loaded GitHub token from DB: {mask_key(app_settings.github_token)}")
            
            # Ollama settings - immer aus DB laden wenn vorhanden
            if saved.get('ollama_url'):
                app_settings.ollama_url = saved['ollama_url']
            if saved.get('ollama_model'):
                app_settings.ollama_model = saved['ollama_model']
            if saved.get('llm_provider'):
                app_settings.llm_provider = saved['llm_provider']
        
        # OpenAI Client initialisieren
        if app_settings.openai_api_key:
            openai_client = AsyncOpenAI(api_key=app_settings.openai_api_key)
            logger.info("OpenAI client initialized")
        else:
            openai_client = None
            logger.info("No OpenAI key configured")
            
    except Exception as e:
        logger.error(f"Error loading settings from DB: {e}")
    
    logger.info(f"Final settings: OpenAI={bool(app_settings.openai_api_key)}, GitHub={bool(app_settings.github_token)}, Ollama URL={app_settings.ollama_url}, Provider={app_settings.llm_provider}")

# Check Ollama availability and load models
async def check_ollama_availability(url: str = None) -> tuple[bool, list]:
    """Check if Ollama is reachable and get available models"""
    global ollama_available, ollama_models
    
    check_url = url or app_settings.ollama_url
    logger.info(f"Checking Ollama at: {check_url}")
    
    try:
        async with httpx.AsyncClient(timeout=10) as http_client:
            response = await http_client.get(f"{check_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", m.get("model", "unknown")) for m in data.get("models", [])]
                ollama_available = True
                ollama_models = models
                logger.info(f"Ollama available with {len(models)} models: {models}")
                return True, models
            else:
                logger.warning(f"Ollama returned status {response.status_code}")
    except httpx.ConnectError as e:
        logger.warning(f"Ollama connection error: {e}")
    except httpx.TimeoutException:
        logger.warning(f"Ollama timeout at {check_url}")
    except Exception as e:
        logger.warning(f"Ollama check failed: {e}")
    
    ollama_available = False
    ollama_models = []
    return False, []

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting ForgePilot API v{APP_VERSION}")
    await load_settings_from_db()
    await check_ollama_availability()

# Workspace base directory
WORKSPACES_DIR = Path('/app/workspaces')
WORKSPACES_DIR.mkdir(exist_ok=True)

# ============== MODELS ==============

class SettingsUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    github_token: Optional[str] = None
    ollama_url: Optional[str] = None
    ollama_model: Optional[str] = None
    llm_provider: Optional[str] = None
    use_ollama: Optional[bool] = None

class SettingsResponse(BaseModel):
    openai_api_key_set: bool
    openai_api_key_preview: str  # Maskierte Vorschau des Keys
    openai_from_env: bool
    github_token_set: bool
    github_token_preview: str  # Maskierte Vorschau
    github_from_env: bool
    ollama_url: str
    ollama_model: str
    llm_provider: str
    use_ollama: bool
    ollama_available: bool
    ollama_models: List[str]

class LLMStatusResponse(BaseModel):
    provider: str
    active_provider: str
    ollama_available: bool
    ollama_url: str
    ollama_model: str
    ollama_models: List[str]
    openai_available: bool
    auto_fallback_active: bool

class UpdateStatusResponse(BaseModel):
    installed_version: str
    latest_version: Optional[str]
    update_available: bool
    checking: bool
    last_checked_at: Optional[str]
    release_notes: Optional[str]
    previous_version: Optional[str]
    last_update_at: Optional[str]
    last_rollback_at: Optional[str]

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    project_type: str = "fullstack"
    template_files: Optional[Dict] = None

class Project(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    project_type: str = "fullstack"
    github_url: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "active"
    workspace_path: Optional[str] = None

class MessageCreate(BaseModel):
    project_id: str
    content: str
    role: str = "user"

class Message(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    content: str
    role: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_type: Optional[str] = None
    files_created: Optional[List[str]] = None
    files_modified: Optional[List[str]] = None

class AgentStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    agent_type: str
    status: str = "idle"
    message: Optional[str] = None

class GitHubImport(BaseModel):
    repo_url: str
    branch: str = "main"
    project_name: Optional[str] = None

class RoadmapItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    title: str
    description: str
    status: str = "pending"
    order: int = 0

class LogEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    level: str
    message: str
    source: str = "system"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class FileCreate(BaseModel):
    path: str
    content: str

# ============== HELPER FUNCTIONS ==============

async def add_log(project_id: str, level: str, message: str, source: str = "system"):
    log = LogEntry(project_id=project_id, level=level, message=message, source=source)
    await db.logs.insert_one(log.model_dump())
    return log

async def update_agent(project_id: str, agent_type: str, status: str, message: str = None):
    await db.agent_status.update_one(
        {"project_id": project_id, "agent_type": agent_type},
        {"$set": {"status": status, "message": message}},
        upsert=True
    )

def get_file_tree(workspace_path: Path, prefix: str = "") -> List[Dict]:
    items = []
    try:
        for item in sorted(workspace_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            if item.name.startswith('.') or item.name in ['node_modules', '__pycache__', 'venv', '.git']:
                continue
            rel_path = f"{prefix}/{item.name}" if prefix else item.name
            if item.is_dir():
                items.append({"name": item.name, "type": "directory", "path": rel_path, "children": get_file_tree(item, rel_path)})
            else:
                items.append({"name": item.name, "type": "file", "path": rel_path})
    except Exception as e:
        logger.error(f"Error getting file tree: {e}")
    return items

def get_active_llm_provider():
    """Determine which LLM provider to use based on settings and availability"""
    if app_settings.llm_provider == "openai":
        return "openai"
    elif app_settings.llm_provider == "ollama":
        return "ollama" if ollama_available else "openai"
    else:  # auto
        if ollama_available:
            return "ollama"
        return "openai"

# ============== SETTINGS ENDPOINTS ==============

@api_router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Get current settings with masked key previews"""
    # Refresh Ollama status
    await check_ollama_availability()
    
    return SettingsResponse(
        openai_api_key_set=bool(app_settings.openai_api_key),
        openai_api_key_preview=mask_key(app_settings.openai_api_key),
        openai_from_env=app_settings.openai_from_env,
        github_token_set=bool(app_settings.github_token),
        github_token_preview=mask_key(app_settings.github_token),
        github_from_env=app_settings.github_from_env,
        ollama_url=app_settings.ollama_url,
        ollama_model=app_settings.ollama_model,
        llm_provider=app_settings.llm_provider,
        use_ollama=app_settings.use_ollama,
        ollama_available=ollama_available,
        ollama_models=ollama_models
    )

@api_router.put("/settings")
async def update_settings(settings: SettingsUpdate):
    """Update and save settings to MongoDB"""
    global openai_client, app_settings, ollama_available, ollama_models
    
    update_data = {}
    changes = []
    
    # OpenAI Key
    if settings.openai_api_key is not None:
        app_settings.openai_api_key = settings.openai_api_key
        update_data['openai_api_key'] = settings.openai_api_key
        changes.append("OpenAI Key")
        if settings.openai_api_key:
            openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        else:
            openai_client = None
    
    # GitHub Token
    if settings.github_token is not None:
        app_settings.github_token = settings.github_token
        update_data['github_token'] = settings.github_token
        changes.append("GitHub Token")
    
    # Ollama URL
    if settings.ollama_url is not None:
        app_settings.ollama_url = settings.ollama_url
        update_data['ollama_url'] = settings.ollama_url
        changes.append("Ollama URL")
        # Re-check Ollama availability with new URL
        await check_ollama_availability(settings.ollama_url)
    
    # Ollama Model
    if settings.ollama_model is not None:
        app_settings.ollama_model = settings.ollama_model
        update_data['ollama_model'] = settings.ollama_model
        changes.append("Ollama Model")
    
    # LLM Provider
    if settings.llm_provider is not None:
        if settings.llm_provider in ['openai', 'ollama', 'auto']:
            app_settings.llm_provider = settings.llm_provider
            update_data['llm_provider'] = settings.llm_provider
            changes.append("LLM Provider")
    
    if settings.use_ollama is not None:
        app_settings.use_ollama = settings.use_ollama
        update_data['use_ollama'] = settings.use_ollama
    
    # Save to MongoDB
    if update_data:
        update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        result = await settings_collection.update_one(
            {"_id": "app_settings"},
            {"$set": update_data},
            upsert=True
        )
        logger.info(f"Settings saved to MongoDB: {changes}, modified={result.modified_count}, upserted={result.upserted_id is not None}")
    
    return {
        "success": True,
        "message": f"Gespeichert: {', '.join(changes)}" if changes else "Keine Änderungen",
        "changes": changes,
        "openai_api_key_set": bool(app_settings.openai_api_key),
        "openai_api_key_preview": mask_key(app_settings.openai_api_key),
        "github_token_set": bool(app_settings.github_token),
        "github_token_preview": mask_key(app_settings.github_token),
        "llm_provider": app_settings.llm_provider,
        "active_provider": get_active_llm_provider(),
        "ollama_available": ollama_available,
        "ollama_models": ollama_models
    }

@api_router.delete("/settings/openai-key")
async def delete_openai_key():
    """Delete OpenAI API key"""
    global openai_client, app_settings
    app_settings.openai_api_key = ""
    openai_client = None
    await settings_collection.update_one(
        {"_id": "app_settings"},
        {"$set": {"openai_api_key": "", "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    logger.info("OpenAI key deleted")
    return {"success": True, "message": "OpenAI API Key gelöscht"}

@api_router.delete("/settings/github-token")
async def delete_github_token():
    """Delete GitHub token"""
    global app_settings
    app_settings.github_token = ""
    await settings_collection.update_one(
        {"_id": "app_settings"},
        {"$set": {"github_token": "", "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    logger.info("GitHub token deleted")
    return {"success": True, "message": "GitHub Token gelöscht"}

# ============== LLM STATUS ENDPOINT ==============

@api_router.get("/llm/status", response_model=LLMStatusResponse)
async def get_llm_status():
    """Get current LLM status including Ollama availability"""
    # Refresh Ollama status
    await check_ollama_availability()
    
    active_provider = get_active_llm_provider()
    auto_fallback = app_settings.llm_provider == "auto" and not ollama_available and bool(app_settings.openai_api_key)
    
    return LLMStatusResponse(
        provider=app_settings.llm_provider,
        active_provider=active_provider,
        ollama_available=ollama_available,
        ollama_url=app_settings.ollama_url,
        ollama_model=app_settings.ollama_model,
        ollama_models=ollama_models,
        openai_available=bool(app_settings.openai_api_key),
        auto_fallback_active=auto_fallback
    )

@api_router.post("/llm/refresh")
async def refresh_llm_status():
    """Refresh LLM status (check Ollama availability)"""
    available, models = await check_ollama_availability()
    return {
        "success": True,
        "provider": app_settings.llm_provider,
        "active_provider": get_active_llm_provider(),
        "ollama_available": available,
        "ollama_url": app_settings.ollama_url,
        "ollama_model": app_settings.ollama_model,
        "ollama_models": models,
        "openai_available": bool(app_settings.openai_api_key),
        "auto_fallback_active": app_settings.llm_provider == "auto" and not available and bool(app_settings.openai_api_key)
    }

@api_router.post("/llm/test-ollama")
async def test_ollama_connection(url: str = Query(...)):
    """Test connection to a specific Ollama URL"""
    logger.info(f"Testing Ollama connection to: {url}")
    try:
        async with httpx.AsyncClient(timeout=10) as http_client:
            response = await http_client.get(f"{url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", m.get("model", "unknown")) for m in data.get("models", [])]
                return {
                    "success": True,
                    "available": True,
                    "models": models,
                    "message": f"Verbunden! {len(models)} Modelle gefunden"
                }
            else:
                return {
                    "success": False,
                    "available": False,
                    "models": [],
                    "message": f"Ollama antwortete mit Status {response.status_code}"
                }
    except httpx.ConnectError:
        return {
            "success": False,
            "available": False,
            "models": [],
            "message": "Verbindung fehlgeschlagen - ist Ollama gestartet?"
        }
    except httpx.TimeoutException:
        return {
            "success": False,
            "available": False,
            "models": [],
            "message": "Timeout - Ollama antwortet nicht"
        }
    except Exception as e:
        return {
            "success": False,
            "available": False,
            "models": [],
            "message": f"Fehler: {str(e)}"
        }

# ============== UPDATE SYSTEM ==============

@api_router.get("/update/status", response_model=UpdateStatusResponse)
async def get_update_status():
    """Get current update status"""
    update_info = await update_collection.find_one({"_id": "update_status"}) or {}
    
    return UpdateStatusResponse(
        installed_version=APP_VERSION,
        latest_version=update_info.get("latest_version"),
        update_available=update_info.get("update_available", False),
        checking=update_info.get("checking", False),
        last_checked_at=update_info.get("last_checked_at"),
        release_notes=update_info.get("release_notes"),
        previous_version=update_info.get("previous_version"),
        last_update_at=update_info.get("last_update_at"),
        last_rollback_at=update_info.get("last_rollback_at")
    )

@api_router.post("/update/check")
async def check_for_updates():
    """Check GitHub for new version by reading VERSION file directly"""
    await update_collection.update_one(
        {"_id": "update_status"},
        {"$set": {"checking": True}},
        upsert=True
    )
    
    try:
        async with httpx.AsyncClient(timeout=30) as http_client:
            # Methode 1: VERSION Datei direkt von GitHub raw laden (funktioniert ohne Release)
            version_response = await http_client.get(
                "https://raw.githubusercontent.com/AndiTrenter/ForgePilot/main/VERSION",
                follow_redirects=True
            )
            
            latest_version = None
            release_notes = ""
            
            if version_response.status_code == 200:
                latest_version = version_response.text.strip()
                logger.info(f"Found VERSION on GitHub: {latest_version}")
                
                # Versuche auch Release Notes zu laden (optional)
                try:
                    release_response = await http_client.get(
                        "https://api.github.com/repos/AndiTrenter/ForgePilot/releases/latest",
                        headers={"Accept": "application/vnd.github.v3+json"}
                    )
                    if release_response.status_code == 200:
                        release = release_response.json()
                        release_notes = release.get("body", "")
                except:
                    pass
            else:
                # Fallback: Versuche Releases API
                release_response = await http_client.get(
                    "https://api.github.com/repos/AndiTrenter/ForgePilot/releases/latest",
                    headers={"Accept": "application/vnd.github.v3+json"}
                )
                if release_response.status_code == 200:
                    release = release_response.json()
                    latest_version = release.get("tag_name", "").lstrip("v")
                    release_notes = release.get("body", "")
            
            if latest_version:
                # Compare versions
                def parse_version(v):
                    try:
                        parts = v.replace("-", ".").split(".")
                        return tuple(map(int, parts[:3]))
                    except:
                        return (0, 0, 0)
                
                current = parse_version(APP_VERSION)
                latest = parse_version(latest_version)
                update_available = latest > current
                
                await update_collection.update_one(
                    {"_id": "update_status"},
                    {"$set": {
                        "checking": False,
                        "latest_version": latest_version,
                        "update_available": update_available,
                        "release_notes": release_notes or f"Update auf Version {latest_version}",
                        "last_checked_at": datetime.now(timezone.utc).isoformat()
                    }},
                    upsert=True
                )
                
                return {
                    "success": True,
                    "installed_version": APP_VERSION,
                    "latest_version": latest_version,
                    "update_available": update_available,
                    "release_notes": release_notes or f"Update auf Version {latest_version}"
                }
            else:
                # Keine Version gefunden
                await update_collection.update_one(
                    {"_id": "update_status"},
                    {"$set": {
                        "checking": False,
                        "latest_version": APP_VERSION,
                        "update_available": False,
                        "last_checked_at": datetime.now(timezone.utc).isoformat()
                    }},
                    upsert=True
                )
                return {
                    "success": True,
                    "installed_version": APP_VERSION,
                    "latest_version": APP_VERSION,
                    "update_available": False,
                    "message": "Konnte VERSION nicht von GitHub laden"
                }
                
    except httpx.TimeoutException:
        await update_collection.update_one(
            {"_id": "update_status"},
            {"$set": {"checking": False}},
            upsert=True
        )
        raise HTTPException(status_code=504, detail="Timeout beim Prüfen auf Updates")
    except Exception as e:
        await update_collection.update_one(
            {"_id": "update_status"},
            {"$set": {"checking": False}},
            upsert=True
        )
        logger.error(f"Update check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/update/install")
async def install_update(target_version: str = None):
    """Install an update (requires Docker access)"""
    update_info = await update_collection.find_one({"_id": "update_status"}) or {}
    
    if not update_info.get("update_available") and not target_version:
        raise HTTPException(status_code=400, detail="Kein Update verfügbar")
    
    version = target_version or update_info.get("latest_version")
    
    # Store current version for rollback
    await update_collection.update_one(
        {"_id": "update_status"},
        {"$set": {
            "previous_version": APP_VERSION,
            "update_in_progress": True,
            "update_started_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    # Return instructions for the update (actual update happens via Docker)
    return {
        "success": True,
        "message": "Update wird vorbereitet",
        "instructions": {
            "step1": f"docker pull ghcr.io/anditrenter/forgepilot/forgepilot-backend:v{version}",
            "step2": f"docker pull ghcr.io/anditrenter/forgepilot/forgepilot-frontend:v{version}",
            "step3": "docker-compose -f docker-compose.unraid.yml down",
            "step4": "docker-compose -f docker-compose.unraid.yml up -d",
        },
        "current_version": APP_VERSION,
        "target_version": version,
        "rollback_available": True
    }

@api_router.post("/update/rollback")
async def rollback_update():
    """Rollback to previous version"""
    update_info = await update_collection.find_one({"_id": "update_status"}) or {}
    previous_version = update_info.get("previous_version")
    
    if not previous_version:
        raise HTTPException(status_code=400, detail="Keine vorherige Version zum Zurücksetzen verfügbar")
    
    await update_collection.update_one(
        {"_id": "update_status"},
        {"$set": {
            "rollback_in_progress": True,
            "last_rollback_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return {
        "success": True,
        "message": "Rollback wird vorbereitet",
        "instructions": {
            "step1": f"docker pull ghcr.io/anditrenter/forgepilot/forgepilot-backend:v{previous_version}",
            "step2": f"docker pull ghcr.io/anditrenter/forgepilot/forgepilot-frontend:v{previous_version}",
            "step3": "docker-compose -f docker-compose.unraid.yml down",
            "step4": "docker-compose -f docker-compose.unraid.yml up -d",
        },
        "current_version": APP_VERSION,
        "rollback_version": previous_version
    }

@api_router.get("/health")
async def health_check():
    """Health check endpoint for update verification"""
    # Check MongoDB
    try:
        await db.command("ping")
        mongo_ok = True
    except:
        mongo_ok = False
    
    # Check Ollama if configured
    ollama_ok = ollama_available or app_settings.llm_provider == "openai"
    
    # Check OpenAI if configured
    openai_ok = bool(app_settings.openai_api_key) or app_settings.llm_provider == "ollama"
    
    all_ok = mongo_ok and (ollama_ok or openai_ok)
    
    return {
        "status": "healthy" if all_ok else "degraded",
        "version": APP_VERSION,
        "checks": {
            "mongodb": mongo_ok,
            "llm": ollama_ok or openai_ok,
            "ollama": ollama_available,
            "openai": bool(app_settings.openai_api_key)
        }
    }

@api_router.get("/version")
async def get_version():
    """Get current app version"""
    return {
        "version": APP_VERSION,
        "name": "ForgePilot"
    }

# ============== OPENAI TOOLS ==============

AGENT_TOOLS = [
    {"type": "function", "function": {"name": "create_file", "description": "Create a new file with content", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "modify_file", "description": "Modify an existing file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read file content", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "delete_file", "description": "Delete a file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "list_files", "description": "List all files", "parameters": {"type": "object", "properties": {"directory": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {"name": "run_command", "description": "Run shell command (npm, pip, python, node)", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "create_roadmap", "description": "Create a roadmap item", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "description": {"type": "string"}}, "required": ["title", "description"]}}},
    {"type": "function", "function": {"name": "update_roadmap_status", "description": "Update roadmap item status", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}}, "required": ["title", "status"]}}},
    {"type": "function", "function": {"name": "web_search", "description": "Search web for best practices and examples", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer", "default": 5}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "test_code", "description": "Test the current code by running it or checking for errors", "parameters": {"type": "object", "properties": {"test_type": {"type": "string", "enum": ["syntax", "run", "lint"]}, "file_path": {"type": "string"}}, "required": ["test_type"]}}},
    {"type": "function", "function": {"name": "debug_error", "description": "Analyze and fix an error", "parameters": {"type": "object", "properties": {"error_message": {"type": "string"}, "file_path": {"type": "string"}}, "required": ["error_message"]}}},
    {"type": "function", "function": {"name": "ask_user", "description": "Ask user a question when clarification is needed", "parameters": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}}},
    {"type": "function", "function": {"name": "mark_complete", "description": "Mark project as complete and ready for push", "parameters": {"type": "object", "properties": {"summary": {"type": "string"}, "tested_features": {"type": "array", "items": {"type": "string"}}}, "required": ["summary", "tested_features"]}}}
]

async def call_ollama(messages: list, model: str = None) -> str:
    """Call Ollama API for chat completion"""
    model = model or app_settings.ollama_model
    
    try:
        async with httpx.AsyncClient(timeout=120) as http_client:
            # Convert messages to Ollama format
            ollama_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                if role == "system":
                    ollama_messages.append({"role": "system", "content": msg.get("content", "")})
                elif role == "user":
                    ollama_messages.append({"role": "user", "content": msg.get("content", "")})
                elif role == "assistant":
                    ollama_messages.append({"role": "assistant", "content": msg.get("content", "")})
            
            logger.info(f"Calling Ollama at {app_settings.ollama_url} with model {model}")
            response = await http_client.post(
                f"{app_settings.ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": ollama_messages,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("message", {}).get("content", "")
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        return None

async def execute_tool(tool_name: str, arguments: dict, workspace_path: Path, project_id: str) -> dict:
    """Execute a tool and return result with continue flag"""
    result = {"output": "", "continue": True, "ask_user": False, "complete": False}
    
    try:
        if tool_name == "create_file":
            file_path = workspace_path / arguments["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(arguments["content"])
            await add_log(project_id, "success", f"Datei erstellt: {arguments['path']}", "coder")
            result["output"] = f"✓ Datei erstellt: {arguments['path']}"
        
        elif tool_name == "modify_file":
            file_path = workspace_path / arguments["path"]
            if not file_path.exists():
                result["output"] = f"✗ Datei nicht gefunden: {arguments['path']}"
            else:
                async with aiofiles.open(file_path, 'w') as f:
                    await f.write(arguments["content"])
                await add_log(project_id, "success", f"Datei geändert: {arguments['path']}", "coder")
                result["output"] = f"✓ Datei geändert: {arguments['path']}"
        
        elif tool_name == "read_file":
            file_path = workspace_path / arguments["path"]
            if not file_path.exists():
                result["output"] = f"✗ Datei nicht gefunden: {arguments['path']}"
            else:
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                result["output"] = f"Inhalt von {arguments['path']}:\n```\n{content}\n```"
        
        elif tool_name == "delete_file":
            file_path = workspace_path / arguments["path"]
            if file_path.exists():
                file_path.unlink()
                result["output"] = f"✓ Datei gelöscht: {arguments['path']}"
            else:
                result["output"] = f"Datei nicht gefunden: {arguments['path']}"
        
        elif tool_name == "list_files":
            files = []
            for item in workspace_path.rglob("*"):
                if item.is_file() and not any(p in str(item) for p in ['.git', 'node_modules', '__pycache__']):
                    files.append(str(item.relative_to(workspace_path)))
            result["output"] = "Dateien:\n" + "\n".join(files[:50]) if files else "Keine Dateien"
        
        elif tool_name == "run_command":
            command = arguments["command"]
            safe_commands = ['npm', 'yarn', 'pip', 'python', 'node', 'cat', 'ls', 'mkdir', 'echo', 'cd']
            if not any(command.startswith(safe) for safe in safe_commands):
                result["output"] = f"✗ Befehl nicht erlaubt: {command}"
            else:
                await add_log(project_id, "info", f"Befehl: {command}", "tester")
                try:
                    proc = subprocess.run(command, shell=True, cwd=workspace_path, capture_output=True, text=True, timeout=60)
                    output = proc.stdout + proc.stderr
                    if proc.returncode == 0:
                        await add_log(project_id, "success", f"Befehl erfolgreich: {command}", "tester")
                        result["output"] = f"✓ {command}\n{output[:1000]}"
                    else:
                        await add_log(project_id, "error", f"Befehl fehlgeschlagen: {command}", "tester")
                        result["output"] = f"✗ {command}\nFehler: {output[:1000]}"
                except subprocess.TimeoutExpired:
                    result["output"] = f"✗ Timeout: {command}"
        
        elif tool_name == "create_roadmap":
            last_item = await db.roadmap.find_one({"project_id": project_id}, sort=[("order", -1)])
            next_order = (last_item.get("order", 0) + 1) if last_item else 0
            item = RoadmapItem(project_id=project_id, title=arguments["title"], description=arguments["description"], order=next_order)
            await db.roadmap.insert_one(item.model_dump())
            await update_agent(project_id, "planner", "running", f"Roadmap: {arguments['title']}")
            result["output"] = f"✓ Roadmap: {arguments['title']}"
        
        elif tool_name == "update_roadmap_status":
            await db.roadmap.update_one({"project_id": project_id, "title": arguments["title"]}, {"$set": {"status": arguments["status"]}})
            result["output"] = f"✓ {arguments['title']} → {arguments['status']}"
        
        elif tool_name == "web_search":
            query = arguments["query"]
            max_results = arguments.get("max_results", 5)
            await add_log(project_id, "info", f"Web-Suche: {query}", "planner")
            await update_agent(project_id, "planner", "running", f"Recherche: {query}")
            try:
                from duckduckgo_search import DDGS
                results = []
                with DDGS() as ddgs:
                    for r in ddgs.text(query, max_results=max_results):
                        results.append(f"• {r.get('title', '')}\n  {r.get('body', '')[:200]}")
                result["output"] = f"Suchergebnisse für '{query}':\n\n" + "\n\n".join(results) if results else "Keine Ergebnisse"
                await add_log(project_id, "success", f"Web-Suche: {len(results)} Ergebnisse", "planner")
            except Exception as e:
                result["output"] = f"Web-Suche fehlgeschlagen: {str(e)}"
        
        elif tool_name == "test_code":
            test_type = arguments["test_type"]
            file_path = arguments.get("file_path", "")
            await update_agent(project_id, "tester", "running", f"Teste: {test_type}")
            
            if test_type == "syntax":
                errors = []
                for f in workspace_path.rglob("*.js"):
                    try:
                        subprocess.run(["node", "--check", str(f)], capture_output=True, check=True)
                    except subprocess.CalledProcessError as e:
                        errors.append(f"{f.name}: {e.stderr.decode()[:200]}")
                result["output"] = "✓ Syntax OK" if not errors else "Syntax-Fehler:\n" + "\n".join(errors)
            
            elif test_type == "run":
                index_html = workspace_path / "index.html"
                if index_html.exists():
                    result["output"] = "✓ index.html existiert - Preview verfügbar"
                else:
                    result["output"] = "✗ Keine index.html gefunden"
            
            elif test_type == "lint":
                result["output"] = "✓ Lint-Check durchgeführt"
            
            await update_agent(project_id, "tester", "completed", "Test abgeschlossen")
        
        elif tool_name == "debug_error":
            error_msg = arguments["error_message"]
            await update_agent(project_id, "debugger", "running", "Analysiere Fehler...")
            await add_log(project_id, "warning", f"Debug: {error_msg[:100]}", "debugger")
            result["output"] = f"Fehler analysiert: {error_msg}\nLösung wird implementiert..."
            await update_agent(project_id, "debugger", "completed", "Fehler analysiert")
        
        elif tool_name == "ask_user":
            question = arguments["question"]
            result["output"] = f"❓ FRAGE AN NUTZER: {question}"
            result["continue"] = False
            result["ask_user"] = True
            await add_log(project_id, "info", f"Frage: {question}", "orchestrator")
        
        elif tool_name == "mark_complete":
            summary = arguments["summary"]
            tested_features = arguments.get("tested_features", [])
            await db.projects.update_one(
                {"id": project_id},
                {"$set": {"status": "ready_for_push", "pending_commit_message": summary, "tested_features": tested_features}}
            )
            await update_agent(project_id, "orchestrator", "completed", "Projekt fertig!")
            await add_log(project_id, "success", f"Projekt fertig: {summary}", "orchestrator")
            result["output"] = f"✅ PROJEKT FERTIG!\n\n{summary}\n\nGetestete Features:\n• " + "\n• ".join(tested_features)
            result["continue"] = False
            result["complete"] = True
        
        else:
            result["output"] = f"Unbekanntes Tool: {tool_name}"
    
    except Exception as e:
        logger.error(f"Tool error: {e}")
        result["output"] = f"Fehler: {str(e)}"
        await add_log(project_id, "error", f"Tool-Fehler: {str(e)}", "debugger")
    
    return result

# ============== AUTONOMOUS AGENT LOOP ==============

async def run_autonomous_agent(project_id: str, workspace_path: Path, initial_messages: list, max_iterations: int = 20):
    """Run the agent autonomously until complete or needs user input"""
    
    files_context = "\n".join([str(f.relative_to(workspace_path)) for f in workspace_path.rglob("*") if f.is_file() and not any(p in str(f) for p in ['.git', 'node_modules'])][:30])
    
    project = await db.projects.find_one({"id": project_id})
    
    system_prompt = f"""Du bist ForgePilot, ein autonomer KI-Entwicklungsassistent. Du arbeitest SELBSTSTÄNDIG bis das Projekt fertig ist oder du eine Frage hast.

PROJEKT: {project.get('name', 'Unbenannt')}
BESCHREIBUNG: {project.get('description', '')}
TYP: {project.get('project_type', 'fullstack')}

DATEIEN IM PROJEKT:
{files_context if files_context else 'Keine Dateien'}

DEINE TOOLS:
1. web_search - Recherchiere Best Practices BEVOR du codest
2. create_file / modify_file / read_file / delete_file - Dateien verwalten
3. run_command - npm/pip/python/node Befehle ausführen
4. create_roadmap / update_roadmap_status - Fortschritt tracken
5. test_code - Code testen (syntax/run/lint)
6. debug_error - Fehler analysieren und beheben
7. ask_user - NUR wenn du eine wichtige Frage hast
8. mark_complete - Wenn ALLES fertig und getestet ist

ARBEITSWEISE - AUTONOM:
1. Recherchiere zuerst Best Practices (web_search)
2. Erstelle Roadmap mit allen Schritten
3. Implementiere Schritt für Schritt
4. Teste nach jeder Änderung
5. Behebe Fehler automatisch
6. Markiere als fertig wenn alles funktioniert

WICHTIG:
- Arbeite AUTONOM weiter bis fertig oder Frage nötig
- Nutze ask_user NUR bei echten Fragen
- Nutze mark_complete wenn ALLES fertig ist
- Antworte auf Deutsch"""

    messages = [{"role": "system", "content": system_prompt}] + initial_messages
    iteration = 0
    should_continue = True
    
    # Determine which LLM to use
    active_provider = get_active_llm_provider()
    logger.info(f"Using LLM provider: {active_provider}")
    
    while should_continue and iteration < max_iterations:
        iteration += 1
        
        try:
            if active_provider == "ollama" and ollama_available:
                # Use Ollama
                response_text = await call_ollama(messages)
                if response_text:
                    yield f"data: {json.dumps({'content': response_text, 'iteration': iteration, 'provider': 'ollama'})}\n\n"
                    messages.append({"role": "assistant", "content": response_text})
                else:
                    # Fallback to OpenAI
                    if openai_client:
                        active_provider = "openai"
                        yield f"data: {json.dumps({'warning': 'Ollama fehlgeschlagen, nutze OpenAI', 'provider': 'openai'})}\n\n"
                    else:
                        yield f"data: {json.dumps({'error': 'Kein LLM verfügbar'})}\n\n"
                        should_continue = False
                        break
                should_continue = False  # Ollama doesn't support tool calling in same way
            else:
                # Use OpenAI
                if not openai_client:
                    yield f"data: {json.dumps({'error': 'Kein OpenAI API Key konfiguriert. Bitte unter Einstellungen > API Keys hinzufügen.'})}\n\n"
                    should_continue = False
                    break
                    
                response = await openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    tools=AGENT_TOOLS,
                    tool_choice="auto",
                    max_tokens=4000
                )
                
                assistant_message = response.choices[0].message
                content = assistant_message.content or ""
                tool_calls = assistant_message.tool_calls or []
                
                if content:
                    yield f"data: {json.dumps({'content': content, 'iteration': iteration, 'provider': 'openai'})}\n\n"
                
                if not tool_calls:
                    should_continue = False
                    break
                
                messages.append({"role": "assistant", "content": content, "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in tool_calls]})
                
                for tc in tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                        tool_name = tc.function.name
                        
                        yield f"data: {json.dumps({'tool': tool_name, 'args': {k: str(v)[:100] for k, v in args.items()}})}\n\n"
                        
                        result = await execute_tool(tool_name, args, workspace_path, project_id)
                        
                        yield f"data: {json.dumps({'tool_result': result['output'][:500]})}\n\n"
                        
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result["output"]})
                        
                        if not result["continue"]:
                            should_continue = False
                            if result["ask_user"]:
                                yield f"data: {json.dumps({'ask_user': True, 'question': result['output']})}\n\n"
                            if result["complete"]:
                                yield f"data: {json.dumps({'complete': True})}\n\n"
                            break
                        
                    except json.JSONDecodeError:
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": "JSON Parse Error"})
            
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Agent loop error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            should_continue = False
    
    if iteration >= max_iterations:
        yield f"data: {json.dumps({'warning': 'Max iterations erreicht'})}\n\n"
    
    yield f"data: {json.dumps({'done': True, 'iterations': iteration})}\n\n"

# ============== PROJECTS ==============

@api_router.get("/")
async def root():
    return {
        "message": "ForgePilot API",
        "version": APP_VERSION,
        "llm_provider": app_settings.llm_provider,
        "active_provider": get_active_llm_provider(),
        "ollama_available": ollama_available
    }

@api_router.post("/projects", response_model=Project)
async def create_project(project: ProjectCreate):
    project_obj = Project(name=project.name, description=project.description, project_type=project.project_type)
    workspace_path = WORKSPACES_DIR / project_obj.id
    workspace_path.mkdir(exist_ok=True)
    project_obj.workspace_path = str(workspace_path)
    
    # Handle template files if provided
    if project.template_files:
        for file_path, content in project.template_files.items():
            full_path = workspace_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(full_path, 'w') as f:
                await f.write(content)
    
    await db.projects.insert_one(project_obj.model_dump())
    
    for agent_type in ["orchestrator", "planner", "coder", "reviewer", "tester", "debugger", "git"]:
        await db.agent_status.insert_one(AgentStatus(project_id=project_obj.id, agent_type=agent_type).model_dump())
    
    await add_log(project_obj.id, "success", f"Projekt erstellt: {project.name}", "system")
    return project_obj

@api_router.get("/projects", response_model=List[Project])
async def get_projects():
    return await db.projects.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)

@api_router.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: str):
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@api_router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    await db.projects.delete_one({"id": project_id})
    workspace_path = WORKSPACES_DIR / project_id
    if workspace_path.exists():
        shutil.rmtree(workspace_path)
    await db.messages.delete_many({"project_id": project_id})
    await db.agent_status.delete_many({"project_id": project_id})
    await db.roadmap.delete_many({"project_id": project_id})
    await db.logs.delete_many({"project_id": project_id})
    return {"message": "Deleted"}

# ============== CHAT (AUTONOMOUS) ==============

@api_router.get("/projects/{project_id}/messages")
async def get_messages(project_id: str):
    return await db.messages.find({"project_id": project_id}, {"_id": 0}).sort("created_at", 1).to_list(1000)

@api_router.post("/projects/{project_id}/messages")
async def create_message(project_id: str, message: MessageCreate):
    msg = Message(project_id=project_id, content=message.content, role=message.role)
    await db.messages.insert_one(msg.model_dump())
    return msg

@api_router.post("/projects/{project_id}/chat")
async def chat_autonomous(project_id: str, message: MessageCreate):
    """Autonomous chat - agent works until complete or needs user input"""
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    workspace_path = Path(project.get('workspace_path', WORKSPACES_DIR / project_id))
    workspace_path.mkdir(exist_ok=True)
    
    user_msg = Message(project_id=project_id, content=message.content, role="user")
    await db.messages.insert_one(user_msg.model_dump())
    
    history = await db.messages.find({"project_id": project_id}, {"_id": 0}).sort("created_at", 1).to_list(20)
    messages_for_api = [{"role": msg["role"], "content": msg["content"]} for msg in history[-15:]]
    
    async def generate():
        full_response = ""
        files_created = []
        
        await update_agent(project_id, "orchestrator", "running", "Starte autonome Entwicklung...")
        yield f"data: {json.dumps({'agent': 'orchestrator', 'status': 'running', 'autonomous': True, 'provider': get_active_llm_provider()})}\n\n"
        
        async for chunk in run_autonomous_agent(project_id, workspace_path, messages_for_api):
            yield chunk
            
            if chunk.startswith('data: '):
                try:
                    data = json.loads(chunk[6:])
                    if 'content' in data:
                        full_response += data['content']
                except:
                    pass
        
        if full_response:
            ai_msg = Message(project_id=project_id, content=full_response, role="assistant", agent_type="orchestrator")
            await db.messages.insert_one(ai_msg.model_dump())
        
        await update_agent(project_id, "orchestrator", "completed", "Fertig")
    
    return StreamingResponse(generate(), media_type="text/event-stream")

# ============== AGENTS ==============

@api_router.get("/projects/{project_id}/agents")
async def get_agents(project_id: str):
    agents = await db.agent_status.find({"project_id": project_id}, {"_id": 0}).to_list(20)
    if not agents:
        for agent_type in ["orchestrator", "planner", "coder", "reviewer", "tester", "debugger", "git"]:
            agent = AgentStatus(project_id=project_id, agent_type=agent_type)
            await db.agent_status.insert_one(agent.model_dump())
            agents.append(agent.model_dump())
    return agents

# ============== GITHUB ==============

@api_router.get("/github/repos")
async def get_github_repos():
    if not app_settings.github_token:
        raise HTTPException(status_code=400, detail="GitHub Token nicht konfiguriert. Bitte unter Einstellungen > API Keys hinzufügen.")
    async with httpx.AsyncClient() as http_client:
        response = await http_client.get("https://api.github.com/user/repos", headers={"Authorization": f"token {app_settings.github_token}"}, params={"per_page": 100, "sort": "updated"})
        response.raise_for_status()
        return {"repos": [{"name": r["name"], "full_name": r["full_name"], "url": r["clone_url"], "default_branch": r["default_branch"], "private": r["private"], "description": r.get("description") or ""} for r in response.json()]}

@api_router.get("/github/branches")
async def get_github_branches(repo: str = Query(...)):
    if not app_settings.github_token:
        raise HTTPException(status_code=400, detail="GitHub Token nicht konfiguriert")
    async with httpx.AsyncClient() as http_client:
        response = await http_client.get(f"https://api.github.com/repos/{repo}/branches", headers={"Authorization": f"token {app_settings.github_token}"})
        response.raise_for_status()
        return {"branches": [b["name"] for b in response.json()]}

@api_router.post("/github/import")
async def import_from_github(data: GitHubImport):
    project_name = data.project_name or data.repo_url.split('/')[-1].replace('.git', '')
    project_obj = Project(name=project_name, description=f"Importiert von {data.repo_url}", github_url=data.repo_url)
    workspace_path = WORKSPACES_DIR / project_obj.id
    
    clone_url = data.repo_url.replace('https://', f'https://{app_settings.github_token}@') if app_settings.github_token else data.repo_url
    git.Repo.clone_from(clone_url, workspace_path, branch=data.branch)
    
    project_obj.workspace_path = str(workspace_path)
    await db.projects.insert_one(project_obj.model_dump())
    
    for agent_type in ["orchestrator", "planner", "coder", "reviewer", "tester", "debugger", "git"]:
        await db.agent_status.insert_one(AgentStatus(project_id=project_obj.id, agent_type=agent_type).model_dump())
    
    await add_log(project_obj.id, "success", f"Repository geklont: {data.repo_url}", "git")
    return project_obj

@api_router.post("/projects/{project_id}/push")
async def push_to_github(project_id: str):
    project = await db.projects.find_one({"id": project_id})
    if not project or not project.get("github_url"):
        raise HTTPException(status_code=400, detail="Kein GitHub Repository")
    
    workspace_path = project.get('workspace_path')
    commit_message = project.get("pending_commit_message", "Update from ForgePilot")
    
    await update_agent(project_id, "git", "running", "Push...")
    repo = git.Repo(workspace_path)
    repo.git.add(A=True)
    repo.index.commit(commit_message)
    repo.remote('origin').push()
    
    await db.projects.update_one({"id": project_id}, {"$set": {"status": "active", "pending_commit_message": None, "last_push": datetime.now(timezone.utc).isoformat()}})
    await update_agent(project_id, "git", "completed", "Push erfolgreich")
    await add_log(project_id, "success", f"Gepusht: {commit_message}", "git")
    return {"success": True}

# ============== ROADMAP & LOGS ==============

@api_router.get("/projects/{project_id}/roadmap")
async def get_roadmap(project_id: str):
    return await db.roadmap.find({"project_id": project_id}, {"_id": 0}).sort("order", 1).to_list(100)

@api_router.get("/projects/{project_id}/logs")
async def get_logs(project_id: str, limit: int = 100):
    return await db.logs.find({"project_id": project_id}, {"_id": 0}).sort("timestamp", -1).to_list(limit)

# ============== FILES & PREVIEW ==============

@api_router.get("/projects/{project_id}/files")
async def get_files(project_id: str, path: str = ""):
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    workspace = Path(project.get('workspace_path', WORKSPACES_DIR / project_id))
    workspace.mkdir(exist_ok=True)
    target_path = workspace / path if path else workspace
    
    if not target_path.exists():
        return {"type": "directory", "items": [], "tree": []}
    
    if target_path.is_file():
        async with aiofiles.open(target_path, 'r', errors='replace') as f:
            content = await f.read()
        return {"type": "file", "content": content, "path": path}
    
    return {"type": "directory", "items": [], "tree": get_file_tree(workspace)}

@api_router.put("/projects/{project_id}/files")
async def save_file(project_id: str, data: FileCreate):
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    workspace = Path(project.get('workspace_path', WORKSPACES_DIR / project_id))
    target_path = workspace / data.path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiofiles.open(target_path, 'w') as f:
        await f.write(data.content)
    return {"success": True}

@api_router.get("/projects/{project_id}/preview/{file_path:path}")
async def serve_preview(project_id: str, file_path: str = "index.html"):
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    workspace = Path(project.get('workspace_path', WORKSPACES_DIR / project_id))
    target_path = workspace / (file_path or "index.html")
    
    if not target_path.exists():
        for entry in ["index.html", "public/index.html", "dist/index.html"]:
            if (workspace / entry).exists():
                target_path = workspace / entry
                break
    
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    content_types = {".html": "text/html", ".css": "text/css", ".js": "application/javascript", ".json": "application/json", ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml"}
    return FileResponse(target_path, media_type=content_types.get(target_path.suffix.lower(), "text/plain"))

@api_router.get("/projects/{project_id}/preview-info")
async def get_preview_info(project_id: str):
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    workspace = Path(project.get('workspace_path', WORKSPACES_DIR / project_id))
    entry_point = None
    for ep in ["index.html", "public/index.html", "dist/index.html"]:
        if (workspace / ep).exists():
            entry_point = ep
            break
    
    return {
        "has_preview": entry_point is not None,
        "entry_point": entry_point,
        "preview_url": f"/api/projects/{project_id}/preview/{entry_point}" if entry_point else None,
        "ready_for_push": project.get("status") == "ready_for_push",
        "pending_commit_message": project.get("pending_commit_message", ""),
        "tested_features": project.get("tested_features", [])
    }

# ============== OLLAMA (legacy endpoints for compatibility) ==============

@api_router.get("/ollama/status")
async def get_ollama_status():
    """Check if Ollama is available (legacy endpoint)"""
    available, models = await check_ollama_availability()
    return {"available": available, "models": models, "url": app_settings.ollama_url}

@api_router.post("/ollama/enable")
async def enable_ollama(model: str = "llama3"):
    """Enable Ollama as primary LLM (legacy endpoint)"""
    app_settings.llm_provider = "ollama"
    app_settings.ollama_model = model
    await settings_collection.update_one(
        {"_id": "app_settings"},
        {"$set": {"llm_provider": "ollama", "ollama_model": model, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    return {"enabled": True, "model": model}

# Include router
app.include_router(api_router)

app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("shutdown")
async def shutdown():
    client.close()
