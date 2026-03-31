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
    deploy_status: Optional[str] = None  # None, "ready", "deploying", "paused", "completed", "failed"
    deploy_started_at: Optional[str] = None
    deploy_completed_at: Optional[str] = None

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

# ============== DEPLOYMENT MODELS ==============

class DeploymentMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    role: str  # "user", "assistant", "system"
    content: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    screenshot_analyzed: bool = False
    commands: Optional[List[str]] = None  # Extracted commands from message

class DeploymentState(BaseModel):
    model_config = ConfigDict(extra="ignore")
    project_id: str
    status: str  # "active", "paused", "completed", "failed"
    current_step: str = ""
    steps_completed: List[str] = []
    context: Dict[str, Any] = {}  # Store deployment context (ports, paths, etc.)
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    paused_at: Optional[str] = None
    completed_at: Optional[str] = None
    screen_sharing_active: bool = False
    last_screenshot_at: Optional[str] = None

class ScreenshotAnalyzeRequest(BaseModel):
    screenshot: str  # base64 encoded image

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
    """Trigger automatic update"""
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
    
    # Trigger the update by creating a trigger file
    trigger_file = Path("/app/workspaces/.update_trigger")
    try:
        trigger_file.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(trigger_file, 'w') as f:
            await f.write(f"version={version}\ntimestamp={datetime.now(timezone.utc).isoformat()}\n")
        
        logger.info(f"Update triggered for version {version}")
        
        return {
            "success": True,
            "message": "Update wird ausgeführt. Die Seite wird in wenigen Sekunden neu geladen.",
            "triggered": True,
            "current_version": APP_VERSION,
            "target_version": version,
            "note": "Der Updater-Service führt das Update durch. Bitte warten..."
        }
    except Exception as e:
        logger.error(f"Failed to trigger update: {e}")
        # Fallback: Return manual instructions
        return {
            "success": True,
            "message": "Automatisches Update nicht möglich. Bitte manuell ausführen.",
            "triggered": False,
            "instructions": {
                "step1": "cd /app/forgepilot",
                "step2": "bash /app/forgepilot/update.sh"
            },
            "current_version": APP_VERSION,
            "target_version": version
        }

@api_router.post("/update/execute")
async def execute_update_script():
    """Execute update script directly (for UI button)"""
    update_info = await update_collection.find_one({"_id": "update_status"}) or {}
    
    if not update_info.get("update_available"):
        raise HTTPException(status_code=400, detail="Kein Update verfügbar")
    
    version = update_info.get("latest_version")
    
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
    
    # Execute update script
    try:
        script_path = Path("/app/forgepilot/update.sh")
        if not script_path.exists():
            script_path = Path("/app/update.sh")
        
        if not script_path.exists():
            raise FileNotFoundError("Update-Script nicht gefunden")
        
        # Execute in background
        subprocess.Popen(
            ["bash", str(script_path)],
            cwd="/app/forgepilot" if Path("/app/forgepilot").exists() else "/app",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        logger.info(f"Update script executed for version {version}")
        
        return {
            "success": True,
            "message": "Update wird ausgeführt. Die Anwendung wird in ca. 30-60 Sekunden neu starten.",
            "current_version": APP_VERSION,
            "target_version": version
        }
    except Exception as e:
        logger.error(f"Failed to execute update script: {e}")
        raise HTTPException(status_code=500, detail=f"Update-Script konnte nicht ausgeführt werden: {str(e)}")

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
            "step3": "cd /app/forgepilot && docker-compose -f /app/forgepilot/docker-compose.unraid.yml down",
            "step4": "cd /app/forgepilot && docker-compose -f /app/forgepilot/docker-compose.unraid.yml up -d",
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
    {"type": "function", "function": {"name": "test_code", "description": "Test the current code by running it or checking for errors", "parameters": {"type": "object", "properties": {"test_type": {"type": "string", "enum": ["syntax", "run", "lint", "completeness"]}, "file_path": {"type": "string"}}, "required": ["test_type"]}}},
    {"type": "function", "function": {"name": "verify_game", "description": "Verify that a game is complete and playable. MUST be called before mark_complete for any game project.", "parameters": {"type": "object", "properties": {"game_type": {"type": "string", "description": "Type of game (e.g., tetris, snake, pong)"}}, "required": ["game_type"]}}},
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
                    # Ensure PATH includes /usr/bin where node is located
                    env = os.environ.copy()
                    env['PATH'] = '/usr/bin:/usr/local/bin:' + env.get('PATH', '')
                    proc = subprocess.run(command, shell=True, cwd=workspace_path, capture_output=True, text=True, timeout=60, env=env)
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
                js_files = list(workspace_path.rglob("*.js"))
                # Ensure PATH includes /usr/bin where node is located
                env = os.environ.copy()
                env['PATH'] = '/usr/bin:/usr/local/bin:' + env.get('PATH', '')
                for f in js_files:
                    try:
                        subprocess.run(["node", "--check", str(f)], capture_output=True, check=True, env=env)
                    except subprocess.CalledProcessError as e:
                        errors.append(f"{f.name}: {e.stderr.decode()[:200]}")
                
                if not js_files:
                    result["output"] = "⚠️ Keine JavaScript-Dateien gefunden"
                elif errors:
                    result["output"] = "✗ Syntax-Fehler gefunden:\n" + "\n".join(errors)
                else:
                    result["output"] = f"✓ Syntax OK ({len(js_files)} JS-Dateien geprüft)"
            
            elif test_type == "run":
                index_html = workspace_path / "index.html"
                if index_html.exists():
                    # Prüfe ob index.html Inhalt hat und JS einbindet
                    content = index_html.read_text()
                    has_script = "<script" in content.lower()
                    has_body = "<body" in content.lower()
                    
                    if not has_body:
                        result["output"] = "✗ index.html hat keinen <body> Tag"
                    elif not has_script:
                        result["output"] = "⚠️ index.html bindet kein JavaScript ein"
                    else:
                        # Prüfe ob script.js existiert und Inhalt hat
                        script_js = workspace_path / "script.js"
                        if script_js.exists():
                            js_content = script_js.read_text()
                            if len(js_content) < 100:
                                result["output"] = "⚠️ script.js ist sehr kurz - möglicherweise unvollständig"
                            elif "addEventListener" in js_content or "requestAnimationFrame" in js_content or "setInterval" in js_content:
                                result["output"] = "✓ index.html und script.js vorhanden - Event-Handling erkannt"
                            else:
                                result["output"] = "⚠️ script.js hat keine Event-Listener - Interaktivität fehlt möglicherweise"
                        else:
                            result["output"] = "⚠️ index.html existiert aber script.js fehlt"
                else:
                    result["output"] = "✗ Keine index.html gefunden - Preview nicht möglich"
            
            elif test_type == "lint":
                # Erweiterte Prüfung
                issues = []
                for js_file in workspace_path.rglob("*.js"):
                    content = js_file.read_text()
                    if "TODO" in content or "FIXME" in content:
                        issues.append(f"{js_file.name}: Enthält TODO/FIXME Kommentare")
                    if "console.log" in content:
                        issues.append(f"{js_file.name}: Enthält console.log (Debug-Code)")
                
                if issues:
                    result["output"] = "⚠️ Lint-Hinweise:\n• " + "\n• ".join(issues)
                else:
                    result["output"] = "✓ Lint-Check OK - Keine Probleme gefunden"
            
            await update_agent(project_id, "tester", "completed", "Test abgeschlossen")
        
        elif tool_name == "verify_game":
            game_type = arguments.get("game_type", "unknown")
            await update_agent(project_id, "tester", "running", f"Verifiziere Spiel: {game_type}")
            
            issues = []
            checks_passed = []
            
            # Check index.html
            index_html = workspace_path / "index.html"
            if not index_html.exists():
                issues.append("❌ index.html fehlt")
            else:
                html_content = index_html.read_text()
                
                # Check for visual elements
                if "<canvas" in html_content.lower():
                    checks_passed.append("✓ Canvas Element gefunden")
                elif "<div" in html_content.lower() and "game" in html_content.lower():
                    checks_passed.append("✓ Game Container gefunden")
                else:
                    issues.append("⚠️ Kein Canvas oder Game-Container in HTML")
                
                # Check for styling
                if "<style" in html_content.lower() or 'style.css' in html_content.lower():
                    checks_passed.append("✓ CSS/Styling vorhanden")
                    # Check if background is styled
                    if "background" in html_content.lower():
                        checks_passed.append("✓ Background-Styling erkannt")
                else:
                    issues.append("⚠️ Kein CSS - Preview könnte weiß/unsichtbar sein!")
                
                if "<script" in html_content.lower():
                    checks_passed.append("✓ Script eingebunden")
                else:
                    issues.append("❌ Kein Script in HTML eingebunden")
                
                # Check for proper script paths (should be relative, not absolute)
                if 'src="/' in html_content or 'href="/' in html_content:
                    issues.append("⚠️ WARNUNG: Absolute Pfade gefunden (src=\"/...\") - verwende relative Pfade!")
            
            # Check JavaScript
            script_js = workspace_path / "script.js"
            if not script_js.exists():
                # Try to find any JS file
                js_files = list(workspace_path.rglob("*.js"))
                if js_files:
                    script_js = js_files[0]
                else:
                    issues.append("❌ Keine JavaScript-Datei gefunden")
            
            if script_js.exists():
                js_content = script_js.read_text()
                js_lines = len(js_content.split('\n'))
                
                if js_lines < 50:
                    issues.append(f"⚠️ JavaScript nur {js_lines} Zeilen - wahrscheinlich unvollständig")
                else:
                    checks_passed.append(f"✓ JavaScript hat {js_lines} Zeilen")
                
                # Check for game essentials
                if "addEventListener" in js_content:
                    checks_passed.append("✓ Event-Listener vorhanden")
                else:
                    issues.append("❌ Keine Event-Listener - Spiel reagiert nicht auf Eingaben")
                
                if "requestAnimationFrame" in js_content or "setInterval" in js_content:
                    checks_passed.append("✓ Game-Loop vorhanden")
                else:
                    issues.append("❌ Kein Game-Loop (requestAnimationFrame/setInterval)")
                
                if "function" in js_content and js_content.count("function") >= 3:
                    checks_passed.append(f"✓ {js_content.count('function')} Funktionen definiert")
                else:
                    issues.append("⚠️ Wenige Funktionen - Code möglicherweise unstrukturiert")
                
                # Check for immediate visual rendering
                if "draw" in js_content.lower() or "render" in js_content.lower():
                    checks_passed.append("✓ Render/Draw Funktion vorhanden")
                    # Check if it's called on page load
                    if "window.onload" in js_content or "DOMContentLoaded" in js_content or "draw()" in js_content or "render()" in js_content:
                        checks_passed.append("✓ Initial rendering beim Laden")
                    else:
                        issues.append("⚠️ Draw/Render wird möglicherweise nicht initial aufgerufen")
                
                # Game-specific checks
                game_lower = game_type.lower()
                if "tetris" in game_lower:
                    if "rotate" in js_content.lower():
                        checks_passed.append("✓ Rotation-Logik erkannt")
                    else:
                        issues.append("⚠️ Keine Rotation-Funktion für Tetris")
                    if "collision" in js_content.lower() or "collide" in js_content.lower():
                        checks_passed.append("✓ Kollisionserkennung vorhanden")
                    else:
                        issues.append("❌ Keine Kollisionserkennung")
                
                elif "snake" in game_lower:
                    if "direction" in js_content.lower():
                        checks_passed.append("✓ Richtungssteuerung erkannt")
                    if "food" in js_content.lower() or "apple" in js_content.lower():
                        checks_passed.append("✓ Food/Apple Logik vorhanden")
                
                elif "pong" in game_lower:
                    if "paddle" in js_content.lower():
                        checks_passed.append("✓ Paddle-Logik erkannt")
                    if "ball" in js_content.lower():
                        checks_passed.append("✓ Ball-Logik vorhanden")
            
            # Summary
            if not issues:
                result["output"] = f"✅ Spiel-Verifikation BESTANDEN\n\n" + "\n".join(checks_passed) + "\n\n🎮 Das Spiel scheint vollständig zu sein!"
            elif len(issues) <= 2 and len(checks_passed) >= 4:
                result["output"] = f"⚠️ Spiel-Verifikation mit Hinweisen:\n\n" + "\n".join(checks_passed) + "\n\nHinweise:\n" + "\n".join(issues) + "\n\nDas Spiel könnte funktionieren, aber prüfe die Hinweise."
            else:
                result["output"] = f"❌ Spiel-Verifikation FEHLGESCHLAGEN\n\nProbleme:\n" + "\n".join(issues) + "\n\nErfolgreich:\n" + "\n".join(checks_passed) + "\n\n⚠️ Das Spiel ist NICHT vollständig. Bitte behebe die Probleme!"
                result["continue"] = True  # Force agent to continue fixing
            
            await update_agent(project_id, "tester", "completed", "Verifikation abgeschlossen")
            await add_log(project_id, "info" if not issues else "warning", f"Spiel-Verifikation: {len(checks_passed)} OK, {len(issues)} Probleme", "tester")
        
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

async def run_autonomous_agent(project_id: str, workspace_path: Path, initial_messages: list, max_iterations: int = 100):
    """Run the agent autonomously until complete or needs user input"""
    
    files_context = "\n".join([str(f.relative_to(workspace_path)) for f in workspace_path.rglob("*") if f.is_file() and not any(p in str(f) for p in ['.git', 'node_modules'])][:30])
    
    project = await db.projects.find_one({"id": project_id})
    
    system_prompt = f"""Du bist ForgePilot, ein EXTREM GENAUER autonomer KI-Entwicklungsassistent. 

🚨🚨🚨 KRITISCH: BISHER HAST DU NUR MÜLL PRODUZIERT! 🚨🚨🚨
Der Nutzer ist EXTREM FRUSTRIERT weil deine bisherigen Projekte NICHT FUNKTIONIEREN!
Leere Previews, nicht spielbare Spiele, weisse Screens - DAS MUSS AUFHÖREN!

Du arbeitest jetzt KONTINUIERLICH und STRIKT bis das Projekt WIRKLICH 100% FUNKTIONIERT.

═══════════════════════════════════════════════════════════════════════════════
                    🚨 ABSOLUTE QUALITÄTSREGELN 🚨
═══════════════════════════════════════════════════════════════════════════════

PROJEKT: {project.get('name', 'Unbenannt')}
BESCHREIBUNG: {project.get('description', '')}
TYP: {project.get('project_type', 'fullstack')}

DATEIEN IM PROJEKT:
{files_context if files_context else 'Keine Dateien'}

═══════════════════════════════════════════════════════════════════════════════
                    ⚡ KONTINUIERLICHER WORKFLOW ⚡
═══════════════════════════════════════════════════════════════════════════════

🎯 DU STOPPST **NIEMALS** OHNE DASS DAS PROJEKT WIRKLICH FUNKTIONIERT!

✅ EINZIGE ERLAUBTE GRÜNDE ZUM STOPPEN:
1. Das Projekt ist KOMPLETT FUNKTIONSFÄHIG - du hast es getestet!
2. Die Preview zeigt ECHTEN INHALT (NICHT weiß/leer/blank)
3. Bei Spielen: Du hast es GESPIELT - Canvas sichtbar, Steuerung funktioniert, Spiel läuft!
4. Du hast verify_game ausgeführt UND alle Checks bestanden
5. Du hast die Preview im Browser geöffnet UND gesehen dass es funktioniert

🚫 ABSOLUT VERBOTEN ZU STOPPEN:
- Nach "Iteration complete" 
- Nach "Code erstellt"
- Nach "Tests bestanden" (wenn Preview noch leer/weiss ist!)
- Wenn Preview nicht lädt oder weiss ist
- Wenn ein Spiel nicht spielbar ist
- Wenn irgendwas NICHT 100% funktioniert
- NIEMALS nach nur einer Iteration!

🔴 WENN PREVIEW LEER/WEISS/NICHT FUNKTIONIERT:
→ DAS IST EIN KRITISCHER FEHLER!
→ STOPPE NICHT! BEHEBE ES SOFORT!
→ Nutze debug_error um den Fehler zu analysieren
→ Nutze modify_file um den Code zu reparieren
→ Teste ERNEUT mit test_code
→ Öffne Preview NOCHMAL
→ Wiederhole bis Preview FUNKTIONIERT!

🎮 SPEZIAL-REGEL FÜR SPIELE:
- Canvas/Spielfeld MUSS SOFORT beim Laden sichtbar sein
- Spielfigur/Elemente MÜSSEN sichtbar sein (NICHT erst nach Tastendruck!)
- Steuerung MUSS sofort reagieren
- verify_game MUSS bestanden werden
- Du MUSST das Spiel selbst "spielen" (simulieren) und testen
- NUR wenn ALLES funktioniert → mark_complete

═══════════════════════════════════════════════════════════════════════════════
                    📋 ARBEITS-PHASEN (OHNE PAUSE!)
═══════════════════════════════════════════════════════════════════════════════

PHASE 1: PLANUNG
- Recherchiere Best Practices (web_search)
- Erstelle Roadmap (create_roadmap)
- DIREKT WEITER ZU PHASE 2!

PHASE 2: IMPLEMENTIERUNG
- Schreibe VOLLSTÄNDIGEN Code (keine TODOs, keine Platzhalter!)
- Nach JEDER Datei: read_file → prüfen → wenn unvollständig: modify_file
- DIREKT WEITER ZU PHASE 3!

PHASE 3: PREVIEW-TEST (KRITISCH!)
🚨🚨🚨 WICHTIGSTE PHASE - OHNE FUNKTIONIERENDES PREVIEW IST ALLES WERTLOS! 🚨🚨🚨

PFLICHT-SCHRITTE:
1. Führe test_code type="syntax" aus → muss bestehen
2. Führe test_code type="run" aus → muss bestehen  
3. Öffne die Preview im Browser (mental simulieren)
4. PRÜFE VISUELL:
   ✅ Ist SOFORT visueller Inhalt sichtbar?
   ✅ Ist der Screen NICHT weiß/leer/blank?
   ✅ Sind Farben/Formen/Text sichtbar?
   ✅ Funktionieren Buttons und Interaktionen?
   ✅ Gibt es Console-Fehler? (NICHT OK!)

WENN PREVIEW LEER/WEISS/KAPUTT:
→ 🚨 KRITISCHER FEHLER! STOPPE NICHT!
→ Nutze debug_error: "Preview ist leer/weiss - analysiere warum"
→ Häufige Ursachen:
   - JavaScript-Fehler (prüfe Console)
   - CSS nicht geladen (prüfe Pfade)
   - Canvas nicht initialisiert (bei Spielen)
   - Event-Listener fehlt
   - Code in falscher Reihenfolge geladen
→ Nutze modify_file um ALLE Fehler zu beheben
→ Teste ERNEUT bis Preview FUNKTIONIERT!

FÜR SPIELE ZUSÄTZLICH:
1. Canvas/Spielfeld MUSS SOFORT sichtbar sein
2. Spielfigur/Elemente MÜSSEN sichtbar sein
3. Steuerung MUSS reagieren (teste mit simulierten Tastendrücken)
4. Führe verify_game aus → MUSS bestanden werden
5. Spiele mental 10 Sekunden → funktioniert alles?

NUR WENN ALLES ✅ → WEITER ZU PHASE 4!

PHASE 4: FINALER CHECK
- test_code (syntax + run)
- verify_game (bei Spielen)
- Lies ALLE Dateien nochmal
- Prüfe Preview ein LETZTES MAL

NUR WENN ALLES ✅:
→ mark_complete

═══════════════════════════════════════════════════════════════════════════════
                    🎮 SPEZIELLE REGELN FÜR SPIELE
═══════════════════════════════════════════════════════════════════════════════

PFLICHT für Spiele:
□ Canvas/Spielfeld ist SOFORT beim Laden sichtbar
□ Spielfigur/Elemente sind sichtbar (NICHT erst nach Tastendruck!)
□ Game-Loop läuft (requestAnimationFrame/setInterval)
□ Steuerung reagiert sofort (Pfeiltasten/Maus)
□ Spiellogik ist vollständig implementiert
□ Kollisionserkennung funktioniert
□ Punkte/Score wird angezeigt und aktualisiert
□ Start/Neustart ist möglich
□ verify_game bestanden

KRITISCH: Ein Spiel ist NICHT "fertig" wenn:
- Canvas weiß/leer ist
- Spielfigur nicht sichtbar ist
- Steuerung nicht reagiert
- Spiellogik fehlt oder defekt ist

═══════════════════════════════════════════════════════════════════════════════
                    🔧 TECHNISCHE STANDARDS
═══════════════════════════════════════════════════════════════════════════════

DATEIEN:
□ index.html im Wurzelverzeichnis
□ CSS/JS im GLEICHEN Ordner (keine relativen Pfade wie "../css/")
□ <script src="script.js"> (NICHT "/assets/script.js")
□ Alle Ressourcen lokal vorhanden

CODE-QUALITÄT:
□ Keine Syntax-Fehler
□ Keine TODOs oder Platzhalter
□ Vollständige Implementierung
□ Event-Listener korrekt eingebunden
□ Console-Fehler-frei

═══════════════════════════════════════════════════════════════════════════════
                    🛠️ DEINE TOOLS
═══════════════════════════════════════════════════════════════════════════════

1. web_search - Recherche BEVOR du codest
2. create_roadmap / update_roadmap_status - Fortschritt tracken
3. create_file / modify_file / read_file / delete_file - Dateiverwaltung
4. run_command - Shell-Befehle
5. test_code - Code testen (syntax/run/lint/completeness)
6. verify_game - PFLICHT für Spiele
7. debug_error - Fehleranalyse
8. ask_user - NUR bei KRITISCHEN Unklarheiten (API Keys, fundamentale Entscheidungen)
9. mark_complete - NUR wenn ALLES funktioniert!

🚨 KRITISCHE REGELN:
- Nutze ask_user NUR für KRITISCHE Blocker (fehlende API Keys, fundamentale User-Entscheidungen)
- Triff alle Design/Tech-Entscheidungen SELBST
- Arbeite KONTINUIERLICH durch bis mark_complete
- STOPPE NICHT nach jeder "Iteration" - arbeite weiter bis FERTIG!

Antworte auf Deutsch."""

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
                
                # CRITICAL: NEVER stop just because there are no tool calls!
                # The agent might be thinking or planning - let it continue!
                # We ONLY stop on:
                # 1. ask_user (critical question)
                # 2. mark_complete (project finished)
                # 3. max_iterations reached
                
                messages.append({"role": "assistant", "content": content, "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in tool_calls]})
                
                # Track if we should continue in THIS iteration
                stop_this_iteration = False
                
                for tc in tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                        tool_name = tc.function.name
                        
                        yield f"data: {json.dumps({'tool': tool_name, 'args': {k: str(v)[:100] for k, v in args.items()}})}\n\n"
                        
                        result = await execute_tool(tool_name, args, workspace_path, project_id)
                        
                        yield f"data: {json.dumps({'tool_result': result['output'][:500]})}\n\n"
                        
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result["output"]})
                        
                        # Only stop on CRITICAL conditions
                        if result.get("ask_user"):
                            # Critical question - stop and wait for user
                            should_continue = False
                            stop_this_iteration = True
                            yield f"data: {json.dumps({'ask_user': True, 'question': result['output'], 'critical': True})}\n\n"
                            break
                        
                        if result.get("complete"):
                            # Project complete - stop gracefully
                            should_continue = False
                            stop_this_iteration = True
                            yield f"data: {json.dumps({'complete': True})}\n\n"
                            break
                        
                        # OTHERWISE: ALWAYS CONTINUE!
                        # Ignore result["continue"] - agent decides when to stop
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": f"JSON Parse Error: {str(e)}"})
                    except Exception as e:
                        logger.error(f"Tool execution error: {e}")
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": f"Tool Error: {str(e)}"})
                
                # If no tool calls and not stopping, force agent to continue
                if not tool_calls and not stop_this_iteration and content:
                    # Agent is just thinking/planning - add a prompt to continue
                    messages.append({
                        "role": "user", 
                        "content": "Fahre fort mit der Arbeit. Nutze Tools um weiterzumachen. STOPPE NICHT!"
                    })
            
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
    """Import project from GitHub repository"""
    try:
        project_name = data.project_name or data.repo_url.split('/')[-1].replace('.git', '')
        project_obj = Project(name=project_name, description=f"Importiert von {data.repo_url}", github_url=data.repo_url)
        workspace_path = WORKSPACES_DIR / project_obj.id
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # Set environment with proper PATH for git
        import_env = os.environ.copy()
        import_env['PATH'] = '/usr/bin:/usr/local/bin:' + import_env.get('PATH', '')
        import_env['GIT_TERMINAL_PROMPT'] = '0'  # Disable interactive prompts
        
        # Prepare clone URL with token if available
        clone_url = data.repo_url
        if app_settings.github_token:
            clone_url = data.repo_url.replace('https://', f'https://{app_settings.github_token}@')
        
        # Clone repository with explicit git path and environment
        logger.info(f"Cloning {data.repo_url} to {workspace_path}")
        git.Repo.clone_from(
            clone_url, 
            workspace_path, 
            branch=data.branch,
            env=import_env
        )
        
        project_obj.workspace_path = str(workspace_path)
        await db.projects.insert_one(project_obj.model_dump())
        
        for agent_type in ["orchestrator", "planner", "coder", "reviewer", "tester", "debugger", "git"]:
            await db.agent_status.insert_one(AgentStatus(project_id=project_obj.id, agent_type=agent_type).model_dump())
        
        await add_log(project_obj.id, "success", f"Repository geklont: {data.repo_url}", "git")
        logger.info(f"Successfully imported {data.repo_url}")
        return project_obj
    
    except git.GitCommandError as e:
        logger.error(f"Git clone failed: {e}")
        raise HTTPException(status_code=400, detail=f"Git clone fehlgeschlagen: {str(e)}")
    except Exception as e:
        logger.error(f"GitHub import failed: {e}")
        raise HTTPException(status_code=500, detail=f"Import fehlgeschlagen: {str(e)}")

@api_router.post("/projects/{project_id}/push")
async def push_to_github(project_id: str):
    """Push project changes to GitHub"""
    try:
        project = await db.projects.find_one({"id": project_id})
        if not project or not project.get("github_url"):
            raise HTTPException(status_code=400, detail="Kein GitHub Repository")
        
        workspace_path = project.get('workspace_path')
        commit_message = project.get("pending_commit_message", "Update from ForgePilot")
        
        # Set environment with proper PATH for git
        git_env = os.environ.copy()
        git_env['PATH'] = '/usr/bin:/usr/local/bin:' + git_env.get('PATH', '')
        git_env['GIT_TERMINAL_PROMPT'] = '0'
        
        await update_agent(project_id, "git", "running", "Push...")
        
        # Use git with explicit environment
        repo = git.Repo(workspace_path)
        with repo.git.custom_environment(**git_env):
            repo.git.add(A=True)
            repo.index.commit(commit_message)
            repo.remote('origin').push()
        
        await db.projects.update_one({"id": project_id}, {"$set": {"status": "active", "pending_commit_message": None, "last_push": datetime.now(timezone.utc).isoformat()}})
        await update_agent(project_id, "git", "completed", "Push erfolgreich")
        await add_log(project_id, "success", f"Gepusht: {commit_message}", "git")
        logger.info(f"Successfully pushed {project_id} to GitHub")
        return {"success": True}
    
    except git.GitCommandError as e:
        logger.error(f"Git push failed: {e}")
        await update_agent(project_id, "git", "idle", "Push fehlgeschlagen")
        await add_log(project_id, "error", f"Push fehlgeschlagen: {str(e)}", "git")
        raise HTTPException(status_code=500, detail=f"Git push fehlgeschlagen: {str(e)}")
    except Exception as e:
        logger.error(f"Push to GitHub failed: {e}")
        await update_agent(project_id, "git", "idle", "Push fehlgeschlagen")
        raise HTTPException(status_code=500, detail=f"Push fehlgeschlagen: {str(e)}")

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

# ============== DEPLOYMENT ENDPOINTS ==============

@api_router.post("/projects/{project_id}/deploy/start")
async def start_deployment(project_id: str):
    """Start deployment for a project"""
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create deployment state
    deployment_state = DeploymentState(
        project_id=project_id,
        status="active",
        current_step="Deployment gestartet. Bitte aktiviere Screen-Sharing.",
        context={}
    )
    
    await db.deployment_states.update_one(
        {"project_id": project_id},
        {"$set": deployment_state.model_dump()},
        upsert=True
    )
    
    # Update project
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {
            "deploy_status": "deploying",
            "deploy_started_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Create initial system message
    initial_msg = DeploymentMessage(
        project_id=project_id,
        role="system",
        content=f"🚀 Deployment gestartet für Projekt: {project.get('name', 'Unknown')}\n\nIch bin dein Deployment-Assistent und werde dich durch den gesamten Installations- und Konfigurationsprozess begleiten.\n\n**Nächster Schritt:** Bitte aktiviere Screen-Sharing, damit ich deinen Bildschirm beobachten und dich optimal unterstützen kann."
    )
    await db.deployment_messages.insert_one(initial_msg.model_dump())
    
    return {"success": True, "deployment_state": deployment_state.model_dump()}

@api_router.get("/projects/{project_id}/deploy/messages")
async def get_deployment_messages(project_id: str):
    """Get all deployment messages"""
    messages = await db.deployment_messages.find(
        {"project_id": project_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(1000)
    return messages

@api_router.get("/projects/{project_id}/deploy/status")
async def get_deployment_status(project_id: str):
    """Get deployment state"""
    state = await db.deployment_states.find_one({"project_id": project_id}, {"_id": 0})
    if not state:
        return {"exists": False}
    return {"exists": True, **state}

@api_router.post("/projects/{project_id}/deploy/pause")
async def pause_deployment(project_id: str):
    """Pause deployment"""
    await db.deployment_states.update_one(
        {"project_id": project_id},
        {"$set": {
            "status": "paused",
            "paused_at": datetime.now(timezone.utc).isoformat(),
            "screen_sharing_active": False
        }}
    )
    
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {"deploy_status": "paused"}}
    )
    
    return {"success": True}

@api_router.post("/projects/{project_id}/deploy/resume")
async def resume_deployment(project_id: str):
    """Resume paused deployment"""
    await db.deployment_states.update_one(
        {"project_id": project_id},
        {"$set": {
            "status": "active",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {"deploy_status": "deploying"}}
    )
    
    return {"success": True}

@api_router.post("/projects/{project_id}/deploy/complete")
async def complete_deployment(project_id: str):
    """Mark deployment as completed"""
    await db.deployment_states.update_one(
        {"project_id": project_id},
        {"$set": {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "screen_sharing_active": False
        }}
    )
    
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {
            "deploy_status": "completed",
            "deploy_completed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"success": True}

@api_router.post("/projects/{project_id}/deploy/analyze")
async def analyze_screenshot(project_id: str, data: ScreenshotAnalyzeRequest):
    """Analyze screenshot with Vision AI and provide deployment guidance"""
    
    # Get deployment state
    state = await db.deployment_states.find_one({"project_id": project_id})
    if not state:
        raise HTTPException(status_code=404, detail="No active deployment found")
    
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Update last screenshot time
    await db.deployment_states.update_one(
        {"project_id": project_id},
        {"$set": {
            "last_screenshot_at": datetime.now(timezone.utc).isoformat(),
            "screen_sharing_active": True
        }}
    )
    
    # Get recent deployment messages for context
    recent_messages = await db.deployment_messages.find(
        {"project_id": project_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)
    recent_messages.reverse()
    
    # Build context
    context_text = f"""
Du bist ein Deployment-Assistent für das Projekt "{project.get('name', 'Unknown')}".

Deployment-Status: {state.get('status')}
Aktueller Schritt: {state.get('current_step', 'Unbekannt')}
Abgeschlossene Schritte: {', '.join(state.get('steps_completed', [])) if state.get('steps_completed') else 'Keine'}

Kontext-Informationen:
{json.dumps(state.get('context', {}), indent=2)}

Bisherige Konversation:
"""
    for msg in recent_messages[-5:]:
        context_text += f"\n{msg['role']}: {msg['content'][:200]}..."
    
    context_text += """

DEINE AUFGABE:
1. Analysiere den Screenshot und erkenne, was der Nutzer gerade auf seinem Bildschirm sieht
2. Identifiziere den aktuellen Schritt im Deployment-Prozess
3. Gib konkrete, ausführbare Befehle oder Anleitungen
4. Wenn du Terminal-Befehle siehst, erkläre was sie tun
5. Wenn du Fehler siehst, analysiere sie und schlage Lösungen vor
6. Wenn Konfiguration nötig ist, gib die exakten Werte vor
7. Sei präzise und hilfreich

Wenn du Befehle vorschlägst, formatiere sie so:
```bash
befehl hier
```

Antworte auf Deutsch."""
    
    try:
        if not openai_client:
            raise HTTPException(status_code=500, detail="OpenAI client not configured")
        
        # Call Vision AI
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": context_text
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analysiere diesen Screenshot und hilf mir beim nächsten Schritt:"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{data.screenshot}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        assistant_response = response.choices[0].message.content
        
        # Extract commands from response (look for code blocks)
        commands = []
        import re
        code_blocks = re.findall(r'```(?:bash|sh)?\n(.*?)\n```', assistant_response, re.DOTALL)
        for block in code_blocks:
            for line in block.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    commands.append(line)
        
        # Save assistant message
        assistant_msg = DeploymentMessage(
            project_id=project_id,
            role="assistant",
            content=assistant_response,
            screenshot_analyzed=True,
            commands=commands if commands else None
        )
        await db.deployment_messages.insert_one(assistant_msg.model_dump())
        
        return {
            "success": True,
            "analysis": assistant_response,
            "commands": commands,
            "message": assistant_msg.model_dump()
        }
        
    except Exception as e:
        logger.error(f"Vision AI analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Screenshot analysis failed: {str(e)}")

@api_router.post("/projects/{project_id}/deploy/message")
async def send_deployment_message(project_id: str, content: str = Body(..., embed=True)):
    """Send a user message in deployment chat"""
    
    state = await db.deployment_states.find_one({"project_id": project_id})
    if not state:
        raise HTTPException(status_code=404, detail="No active deployment found")
    
    # Save user message
    user_msg = DeploymentMessage(
        project_id=project_id,
        role="user",
        content=content
    )
    await db.deployment_messages.insert_one(user_msg.model_dump())
    
    # Get context
    project = await db.projects.find_one({"id": project_id})
    recent_messages = await db.deployment_messages.find(
        {"project_id": project_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)
    recent_messages.reverse()
    
    # Build conversation
    conversation = [
        {
            "role": "system",
            "content": f"""Du bist ein Deployment-Assistent für das Projekt "{project.get('name', 'Unknown')}".

Deployment-Status: {state.get('status')}
Aktueller Schritt: {state.get('current_step', 'Unbekannt')}

Hilf dem Nutzer bei der Installation und Konfiguration auf Unraid.
Gib konkrete Befehle und Anleitungen.
Wenn du Befehle vorschlägst, formatiere sie so:
```bash
befehl hier
```

Antworte auf Deutsch."""
        }
    ]
    
    for msg in recent_messages[-5:]:
        if msg['role'] != 'system':
            conversation.append({
                "role": msg['role'],
                "content": msg['content']
            })
    
    try:
        if not openai_client:
            raise HTTPException(status_code=500, detail="OpenAI client not configured")
        
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=conversation,
            max_tokens=800
        )
        
        assistant_response = response.choices[0].message.content
        
        # Extract commands
        commands = []
        import re
        code_blocks = re.findall(r'```(?:bash|sh)?\n(.*?)\n```', assistant_response, re.DOTALL)
        for block in code_blocks:
            for line in block.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    commands.append(line)
        
        # Save assistant message
        assistant_msg = DeploymentMessage(
            project_id=project_id,
            role="assistant",
            content=assistant_response,
            commands=commands if commands else None
        )
        await db.deployment_messages.insert_one(assistant_msg.model_dump())
        
        return {
            "success": True,
            "message": assistant_msg.model_dump()
        }
        
    except Exception as e:
        logger.error(f"Chat response failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat response failed: {str(e)}")

# Include router
app.include_router(api_router)

app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("shutdown")
async def shutdown():
    client.close()
