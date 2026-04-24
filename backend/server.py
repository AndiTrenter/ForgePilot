from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query, Body
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import sys
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
import yaml

ROOT_DIR = Path(__file__).parent
APP_ROOT = ROOT_DIR.parent
load_dotenv(ROOT_DIR / '.env')

# Ensure critical environment variables are available for subprocess execution
# Supervisor may not pass all env vars, so we set defaults for missing ones
if 'HOME' not in os.environ:
    os.environ['HOME'] = '/root'
if 'PLAYWRIGHT_BROWSERS_PATH' not in os.environ:
    # Check common playwright browser locations
    for path in ['/pw-browsers', '/root/.cache/ms-playwright']:
        if os.path.isdir(path):
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = path
            break
if 'USER' not in os.environ:
    os.environ['USER'] = 'root'

# App Version
APP_VERSION = "3.0.0"
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

# ForgePilot Delivery Layer (Approval-Gates + Stage-Machine)
from policy_engine import evaluate_action as policy_evaluate, needs_approval as policy_needs_approval, is_forbidden as policy_is_forbidden  # noqa: E402
from deploy_orchestrator import DeliveryOrchestrator, DeliveryStage  # noqa: E402
delivery_orchestrator = DeliveryOrchestrator(db)

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
    # Delivery-Result-Poller starten (finalisiert Jobs nach Deploy)
    asyncio.create_task(_delivery_result_poller())


async def _delivery_result_poller():
    """Prüft regelmäßig, ob updater-service.sh einen Deploy fertiggestellt hat
    und setzt den zugehörigen Delivery-Job auf DONE.
    """
    result_paths = [
        Path("/app/workspaces/.deploy_result"),
        Path("/mnt/user/appdata/forgepilot/.deploy_result"),
    ]
    while True:
        try:
            for p in result_paths:
                if p.exists():
                    try:
                        data = json.loads(p.read_text())
                    except Exception:
                        data = {}
                    job_id = data.get("job_id")
                    if job_id:
                        job = await delivery_orchestrator.get_job(job_id)
                        if job and job["stage"] == DeliveryStage.DEPLOYING.value:
                            await delivery_orchestrator.finalize_job(
                                job_id,
                                result={
                                    "deployed": True,
                                    "finished_at": data.get("finished_at"),
                                    "project_id": data.get("project_id"),
                                },
                            )
                            await delivery_orchestrator.append_log(
                                job_id, "info", "Deploy durch updater-service abgeschlossen."
                            )
                    try:
                        p.unlink()
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"delivery_result_poller error: {e}")
        await asyncio.sleep(5)

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

@api_router.get("/update/execute-live")
async def execute_update_live():
    """Execute update script with live output streaming (Server-Sent Events)"""
    from fastapi.responses import StreamingResponse
    import asyncio
    
    async def generate_output():
        """Stream update script output line by line"""
        # HARDCODED: Unraid verwendet updater-service.sh im Root
        update_script = Path("/mnt/user/appdata/forgepilot/updater-service.sh")
        
        # Fallback für Dev-Umgebung
        if not update_script.exists():
            update_script = Path("/app/update.sh")
        
        # Check if script exists
        if not update_script.exists():
            yield f"data: {{\"type\": \"error\", \"message\": \"Update-Script nicht gefunden: {update_script}. Bitte stellen Sie sicher, dass updater-service.sh im Hauptverzeichnis existiert.\"}}\n\n"
            return
        
        yield f"data: {{\"type\": \"info\", \"message\": \"ForgePilot Update Script\"}}\n\n"
        yield f"data: {{\"type\": \"info\", \"message\": \"Script gefunden: {update_script}\"}}\n\n"
        yield f"data: {{\"type\": \"info\", \"message\": \"Starte Update...\"}}\n\n"
        
        try:
            # Execute the update script
            process = await asyncio.create_subprocess_exec(
                "bash",
                str(update_script),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(update_script.parent)
            )
            
            # Stream output line by line
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                output = line.decode('utf-8').rstrip()
                if output:
                    # Send each line as SSE event
                    import json
                    yield f"data: {json.dumps({'type': 'output', 'message': output})}\n\n"
                    await asyncio.sleep(0.01)  # Small delay for smooth streaming
            
            # Wait for process to complete
            await process.wait()
            
            if process.returncode == 0:
                yield f"data: {{\"type\": \"success\", \"message\": \"✅ Update erfolgreich abgeschlossen!\"}}\n\n"
            else:
                yield f"data: {{\"type\": \"error\", \"message\": \"❌ Update mit Fehler beendet (Exit Code: {process.returncode})\"}}\n\n"
            
            yield f"data: {{\"type\": \"done\"}}\n\n"
            
        except Exception as e:
            logger.error(f"Update execution error: {e}")
            import json
            yield f"data: {json.dumps({'type': 'error', 'message': f'Fehler: {str(e)}'})}\n\n"
            yield f"data: {{\"type\": \"done\"}}\n\n"
    
    return StreamingResponse(
        generate_output(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@api_router.post("/update/execute")
async def execute_update_script():
    """Execute update script directly (for UI button) with root privileges"""
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
    
    # Execute update script with root privileges
    try:
        # Check multiple possible locations (most common first)
        possible_paths = [
            Path("/app/update.sh"),  # Default location (development/container)
            Path("/mnt/user/appdata/forgepilot/update.sh"),  # Unraid deployment
            Path("/app/forgepilot/update.sh"),  # Alternative deployment
        ]
        
        script_path = None
        for path in possible_paths:
            if path.exists():
                script_path = path
                break
        
        if not script_path:
            raise FileNotFoundError(f"Update-Script nicht gefunden. Geprüfte Pfade: {[str(p) for p in possible_paths]}")
        
        # Get working directory
        work_dir = script_path.parent
        
        # Create popup command for user
        popup_command = f"cd {work_dir} && sudo bash {script_path.name}"
        
        logger.info(f"Executing update script: {script_path}")
        logger.info(f"Working directory: {work_dir}")
        logger.info(f"Command for user: {popup_command}")
        
        # Execute with sudo (will work if sudoers is configured or running as root)
        proc = subprocess.Popen(
            ["sudo", "bash", str(script_path)],
            cwd=str(work_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Don't wait for completion (background execution)
        logger.info(f"Update script started with PID {proc.pid}")
        
        return {
            "success": True,
            "message": f"Update wird ausgeführt auf Version {version}.\n\nDie Anwendung wird in ca. 30-60 Sekunden neu starten.",
            "current_version": APP_VERSION,
            "target_version": version,
            "script_path": str(script_path),
            "working_directory": str(work_dir),
            "command": popup_command,
            "pid": proc.pid,
            "note": "Falls Update fehlschlägt, führe manuell aus:",
            "manual_command": popup_command
        }
    except PermissionError as e:
        error_msg = f"Keine Root-Rechte. Bitte manuell ausführen:\n\n{popup_command}"
        logger.error(f"Permission denied: {e}")
        return {
            "success": False,
            "message": error_msg,
            "command": popup_command,
            "error": "Permission denied - Root-Rechte erforderlich"
        }
    except Exception as e:
        logger.error(f"Failed to execute update script: {e}")
        error_detail = f"Update-Script konnte nicht ausgeführt werden: {str(e)}"
        if script_path:
            error_detail += f"\n\nManuell ausführen:\n{popup_command}"
        raise HTTPException(status_code=500, detail=error_detail)

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
    {"type": "function", "function": {"name": "search_replace", "description": "PREFERRED over modify_file! Precise edits: find old_str and replace with new_str. Much faster and safer.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "File path"}, "old_str": {"type": "string", "description": "Exact string to find (must match exactly!)"}, "new_str": {"type": "string", "description": "Replacement string"}}, "required": ["path", "old_str", "new_str"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read file content", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "view_file", "description": "View file with optional line range. Better than read_file for large files.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "File path"}, "start_line": {"type": "integer", "description": "Start line (optional)"}, "end_line": {"type": "integer", "description": "End line (optional)"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "view_bulk", "description": "View multiple files at once. Much faster than reading one by one.", "parameters": {"type": "object", "properties": {"paths": {"type": "array", "items": {"type": "string"}, "description": "List of file paths to view"}}, "required": ["paths"]}}},
    {"type": "function", "function": {"name": "glob_files", "description": "Find files by pattern (e.g., '**/*.js', 'src/**/*.py')", "parameters": {"type": "object", "properties": {"pattern": {"type": "string", "description": "Glob pattern"}}, "required": ["pattern"]}}},
    {"type": "function", "function": {"name": "lint_javascript", "description": "Lint JavaScript/TypeScript files with ESLint. Finds syntax errors, unused variables, etc.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "File or directory to lint"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "lint_python", "description": "Lint Python files with ruff. Finds syntax errors, unused imports, style issues.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "File or directory to lint"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "screenshot", "description": "Take screenshot of the preview to visually validate UI. Checks layout, colors, buttons visibility.", "parameters": {"type": "object", "properties": {"url": {"type": "string", "description": "URL to screenshot (optional, defaults to preview)"}}, "required": []}}},
    {"type": "function", "function": {"name": "delete_file", "description": "Delete a file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "list_files", "description": "List all files", "parameters": {"type": "object", "properties": {"directory": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {"name": "run_command", "description": "Run shell command (npm, pip, python, node)", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "setup_docker_service", "description": "Setup Docker service (MongoDB, PostgreSQL, Redis, MySQL, etc.) via docker-compose. Creates docker-compose.yml with the service.", "parameters": {"type": "object", "properties": {"service_type": {"type": "string", "enum": ["mongodb", "postgresql", "mysql", "redis", "elasticsearch", "rabbitmq", "custom"], "description": "Type of service to setup"}, "service_name": {"type": "string", "description": "Name for the service container"}, "port": {"type": "integer", "description": "Port to expose (optional)"}, "custom_config": {"type": "object", "description": "Custom docker-compose config for service (optional)"}}, "required": ["service_type", "service_name"]}}},
    {"type": "function", "function": {"name": "install_package", "description": "Install npm or pip package in the project", "parameters": {"type": "object", "properties": {"package_manager": {"type": "string", "enum": ["npm", "pip", "yarn"], "description": "Package manager to use"}, "package_name": {"type": "string", "description": "Package name to install"}, "save_dev": {"type": "boolean", "default": False, "description": "Save as dev dependency (npm only)"}}, "required": ["package_manager", "package_name"]}}},
    {"type": "function", "function": {"name": "browser_test", "description": "CRITICAL: Test app in browser like a real user. MUST be called before mark_complete! Opens preview, fills forms, clicks buttons, validates functionality.", "parameters": {"type": "object", "properties": {"test_scenarios": {"type": "array", "items": {"type": "string"}, "description": "List of scenarios to test (e.g., 'Fill contact form and submit', 'Click all navigation links', 'Test recipe search')"}, "preview_url": {"type": "string", "description": "URL to test (default: uses project preview)"}}, "required": ["test_scenarios"]}}},
    {"type": "function", "function": {"name": "build_app", "description": "Build React/Vue/Vite app for production. Runs 'npm run build' or 'yarn build'. MUST be called before preview/testing for React/Vue apps!", "parameters": {"type": "object", "properties": {"build_command": {"type": "string", "description": "Custom build command (optional, defaults to 'npm run build')", "default": "npm run build"}}, "required": []}}},
    {"type": "function", "function": {"name": "troubleshoot", "description": "Call when STUCK after 2-3 failed attempts. Expert analyzes problem and suggests alternative solutions.", "parameters": {"type": "object", "properties": {"problem": {"type": "string", "description": "What are you stuck on?"}, "attempted_solutions": {"type": "array", "items": {"type": "string"}, "description": "What have you tried?"}}, "required": ["problem", "attempted_solutions"]}}},
    {"type": "function", "function": {"name": "get_integration_playbook", "description": "Get expert playbook for 3rd party APIs (OpenAI, Stripe, etc.). Returns latest SDKs, code examples, best practices.", "parameters": {"type": "object", "properties": {"integration": {"type": "string", "description": "e.g., 'OpenAI GPT-4', 'Stripe Payment', 'MongoDB'"}, "use_case": {"type": "string", "description": "What do you want to do?"}}, "required": ["integration"]}}},
    {"type": "function", "function": {"name": "get_design_guidelines", "description": "Get professional UI/UX design guidelines. Returns color schemes, layouts, component design.", "parameters": {"type": "object", "properties": {"app_type": {"type": "string", "description": "e.g., 'dashboard', 'landing_page', 'ecommerce'"}, "style": {"type": "string", "description": "e.g., 'modern', 'minimalist', 'playful' (optional)"}}, "required": ["app_type"]}}},
    {"type": "function", "function": {"name": "advanced_test", "description": "Advanced testing with Playwright (UI) and curl (Backend). More thorough than browser_test.", "parameters": {"type": "object", "properties": {"test_type": {"type": "string", "enum": ["ui", "backend", "both"], "description": "What to test"}, "test_scenarios": {"type": "array", "items": {"type": "string"}, "description": "Detailed test scenarios"}}, "required": ["test_type", "test_scenarios"]}}},
    {"type": "function", "function": {"name": "think", "description": "Log your thought process. Use this to show transparency: what you're thinking, planning, considering. User sees WHY you do things.", "parameters": {"type": "object", "properties": {"thought": {"type": "string", "description": "Your current thoughts/reasoning"}}, "required": ["thought"]}}},
    {"type": "function", "function": {"name": "code_review", "description": "Review all code before mark_complete. Checks for: clean code, best practices, security, performance.", "parameters": {"type": "object", "properties": {"files_to_review": {"type": "array", "items": {"type": "string"}, "description": "List of file paths to review"}}, "required": []}}},
    {"type": "function", "function": {"name": "update_memory", "description": "Update project memory/requirements. Track what user wants, decisions made, features completed.", "parameters": {"type": "object", "properties": {"memory_type": {"type": "string", "enum": ["requirements", "decisions", "features", "notes"], "description": "Type of memory to update"}, "content": {"type": "string", "description": "What to remember"}}, "required": ["memory_type", "content"]}}},
    {"type": "function", "function": {"name": "git_commit", "description": "Commit current changes to git. Use after completing a feature.", "parameters": {"type": "object", "properties": {"message": {"type": "string", "description": "Commit message"}}, "required": ["message"]}}},
    {"type": "function", "function": {"name": "create_roadmap", "description": "Create a roadmap item", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "description": {"type": "string"}}, "required": ["title", "description"]}}},
    {"type": "function", "function": {"name": "update_roadmap_status", "description": "Update roadmap item status", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}}, "required": ["title", "status"]}}},
    {"type": "function", "function": {"name": "web_search", "description": "Search web for best practices and examples", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer", "default": 5}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "test_code", "description": "Test the current code by running it or checking for errors", "parameters": {"type": "object", "properties": {"test_type": {"type": "string", "enum": ["syntax", "run", "lint", "completeness"]}, "file_path": {"type": "string"}}, "required": ["test_type"]}}},
    {"type": "function", "function": {"name": "verify_game", "description": "Verify that a game is complete and playable. MUST be called before mark_complete for any game project.", "parameters": {"type": "object", "properties": {"game_type": {"type": "string", "description": "Type of game (e.g., tetris, snake, pong)"}}, "required": ["game_type"]}}},
    {"type": "function", "function": {"name": "debug_error", "description": "Analyze and fix an error", "parameters": {"type": "object", "properties": {"error_message": {"type": "string"}, "file_path": {"type": "string"}}, "required": ["error_message"]}}},
    {"type": "function", "function": {"name": "ask_user", "description": "Ask user ONLY when truly needed. DO NOT ask about technology choices (DB, framework) - choose the best yourself!", "parameters": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}}},
    {"type": "function", "function": {"name": "mark_complete", "description": "Mark project as complete. MUST call browser_test BEFORE this!", "parameters": {"type": "object", "properties": {"summary": {"type": "string"}, "tested_features": {"type": "array", "items": {"type": "string"}}}, "required": ["summary", "tested_features"]}}},
    {"type": "function", "function": {"name": "clear_errors", "description": "Clear old error logs that have been resolved. Call this BEFORE mark_complete if there are old errors from earlier failed attempts that are now fixed.", "parameters": {"type": "object", "properties": {"reason": {"type": "string", "description": "Why the errors are resolved (e.g., 'Build now succeeds after fixing config')"}}, "required": ["reason"]}}}
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

async def generate_alternative_query(original_query: str, attempt: int) -> str:
    """Generate alternative search query using LLM"""
    try:
        prompt = f"""Du bist ein Experte für Web-Recherchen. Die folgende Suchanfrage hat keine guten Ergebnisse geliefert:

"{original_query}"

Generiere eine alternative, bessere Suchanfrage (Versuch {attempt}/3). 
- Verwende andere Formulierungen
- Füge relevante technische Begriffe hinzu
- Versuche spezifischere oder breitere Suchbegriffe
- Gib nur die neue Suchanfrage zurück, ohne Erklärung

Alternative Suchanfrage:"""

        provider = get_active_llm_provider()
        
        if provider == "openai" and openai_client:
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.8
            )
            alternative = response.choices[0].message.content.strip()
            return alternative.strip('"').strip()
        
        elif provider == "ollama" and ollama_available:
            alternative = await call_ollama([{"role": "user", "content": prompt}])
            if alternative:
                return alternative.strip('"').strip()
        
        # Fallback: Simple variation
        variations = [
            f"{original_query} best practices",
            f"{original_query} tutorial guide",
            f"how to {original_query}"
        ]
        return variations[attempt - 1] if attempt <= len(variations) else original_query
        
    except Exception as e:
        logger.error(f"Query generation failed: {e}")
        # Fallback variations
        return f"{original_query} tutorial" if attempt == 1 else f"{original_query} best practices"

async def execute_tool(tool_name: str, arguments: dict, workspace_path: Path, project_id: str) -> dict:
    """Execute a tool and return result with continue flag"""
    result = {"output": "", "continue": True, "ask_user": False, "complete": False}
    
    # Map tools to agent types for status updates
    tool_agent_map = {
        "create_file": "coder",
        "modify_file": "coder",
        "search_replace": "coder",
        "read_file": "reviewer",
        "view_file": "reviewer",
        "view_bulk": "reviewer",
        "glob_files": "reviewer",
        "lint_javascript": "reviewer",
        "lint_python": "reviewer",
        "screenshot": "tester",
        "delete_file": "coder",
        "list_files": "coder",
        "create_roadmap": "planner",
        "update_roadmap_status": "planner",
        "web_search": "planner",
        "test_code": "tester",
        "verify_game": "tester",
        "browser_test": "tester",
        "advanced_test": "tester",
        "debug_error": "debugger",
        "troubleshoot": "debugger",
        "run_command": "tester",
        "build_app": "coder",
        "setup_docker_service": "coder",
        "install_package": "coder",
        "get_integration_playbook": "planner",
        "get_design_guidelines": "planner",
        "think": "orchestrator",
        "code_review": "reviewer",
        "update_memory": "orchestrator",
        "git_commit": "git",
        "mark_complete": "orchestrator",
        "clear_errors": "orchestrator",
        "ask_user": "orchestrator"
    }
    
    agent_type = tool_agent_map.get(tool_name, "orchestrator")
    
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
        
        elif tool_name == "search_replace":
            file_path = workspace_path / arguments["path"]
            old_str = arguments["old_str"]
            new_str = arguments["new_str"]
            
            if not file_path.exists():
                result["output"] = f"✗ Datei nicht gefunden: {arguments['path']}"
            else:
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                
                if old_str not in content:
                    result["output"] = f"✗ String nicht gefunden in {arguments['path']}"
                else:
                    new_content = content.replace(old_str, new_str, 1)
                    async with aiofiles.open(file_path, 'w') as f:
                        await f.write(new_content)
                    result["output"] = f"✓ Ersetzt in {arguments['path']}"
                    await add_log(project_id, "success", f"search_replace: {arguments['path']}", "coder")
        
        elif tool_name == "view_file":
            file_path = workspace_path / arguments["path"]
            start_line = arguments.get("start_line")
            end_line = arguments.get("end_line")
            
            if not file_path.exists():
                result["output"] = f"✗ Datei nicht gefunden: {arguments['path']}"
            else:
                async with aiofiles.open(file_path, 'r') as f:
                    lines = await f.readlines()
                
                if start_line and end_line:
                    selected_lines = lines[start_line-1:end_line]
                    result["output"] = f"[Lines {start_line}-{end_line} of {len(lines)}]\n" + "".join(selected_lines)
                else:
                    result["output"] = "".join(lines[:2000])
        
        elif tool_name == "view_bulk":
            paths = arguments["paths"]
            outputs = []
            
            for path_str in paths[:10]:
                file_path = workspace_path / path_str
                if file_path.exists():
                    async with aiofiles.open(file_path, 'r') as f:
                        content = await f.read()
                    outputs.append(f"\n=== {path_str} ===\n{content[:1000]}")
                else:
                    outputs.append(f"\n=== {path_str} ===\n✗ Not found")
            
            result["output"] = "\n".join(outputs)
        
        elif tool_name == "glob_files":
            pattern = arguments["pattern"]
            
            try:
                matches = []
                for file in workspace_path.rglob(pattern.lstrip("**/").lstrip("/")):
                    if file.is_file():
                        rel_path = file.relative_to(workspace_path)
                        matches.append(str(rel_path))
                
                result["output"] = f"Found {len(matches)} files:\n" + "\n".join(matches[:50])
            except Exception as e:
                result["output"] = f"✗ Glob error: {str(e)}"

        
        elif tool_name == "delete_file":
            file_path = workspace_path / arguments["path"]
            if file_path.exists():
                file_path.unlink()
                await add_log(project_id, "success", f"Datei gelöscht: {arguments['path']}", "coder")
                result["output"] = f"✓ Datei gelöscht: {arguments['path']}"
            else:
                result["output"] = f"✗ Datei nicht gefunden: {arguments['path']}"
        
        elif tool_name == "lint_javascript":
            path = arguments["path"]
            target_path = workspace_path / path
            
            await update_agent(project_id, "reviewer", "running", f"Linting: {path}")
            await add_log(project_id, "info", f"🔍 Lint JavaScript: {path}", "reviewer")
            
            try:
                env = os.environ.copy()
                env['PATH'] = '/usr/bin:/usr/local/bin:/bin:' + env.get('PATH', '')
                
                # Simple syntax check with node
                proc = subprocess.run(
                    ["node", "--check", str(target_path)] if target_path.is_file() else ["echo", "Directory linting not implemented"],
                    capture_output=True,
                    text=True,
                    env=env,
                    cwd=workspace_path
                )
                
                if proc.returncode == 0:
                    result["output"] = f"✅ JavaScript Lint: No errors in {path}"
                    await add_log(project_id, "success", f"Lint: {path} OK", "reviewer")
                else:
                    result["output"] = f"❌ JavaScript Lint Errors:\n{proc.stderr}"
                    await add_log(project_id, "error", f"Lint errors in {path}", "reviewer")
                
                await update_agent(project_id, "reviewer", "completed", "Lint done")
            except Exception as e:
                result["output"] = f"❌ Lint error: {str(e)}"
                await add_log(project_id, "error", f"Lint failed: {str(e)}", "reviewer")
        
        elif tool_name == "lint_python":
            path = arguments["path"]
            target_path = workspace_path / path
            
            await update_agent(project_id, "reviewer", "running", f"Linting: {path}")
            await add_log(project_id, "info", f"🔍 Lint Python: {path}", "reviewer")
            
            try:
                env = os.environ.copy()
                env['PATH'] = '/usr/bin:/usr/local/bin:/bin:' + env.get('PATH', '')
                
                # Check syntax with python
                proc = subprocess.run(
                    ["python3", "-m", "py_compile", str(target_path)] if target_path.is_file() else ["echo", "Directory linting not implemented"],
                    capture_output=True,
                    text=True,
                    env=env,
                    cwd=workspace_path
                )
                
                if proc.returncode == 0:
                    result["output"] = f"✅ Python Lint: No errors in {path}"
                    await add_log(project_id, "success", f"Lint: {path} OK", "reviewer")
                else:
                    result["output"] = f"❌ Python Lint Errors:\n{proc.stderr}"
                    await add_log(project_id, "error", f"Lint errors in {path}", "reviewer")
                
                await update_agent(project_id, "reviewer", "completed", "Lint done")
            except Exception as e:
                result["output"] = f"❌ Lint error: {str(e)}"
                await add_log(project_id, "error", f"Lint failed: {str(e)}", "reviewer")
        
        elif tool_name == "screenshot":
            url = arguments.get("url", "")
            
            await update_agent(project_id, "tester", "running", "Screenshot...")
            await add_log(project_id, "info", "📸 Taking screenshot", "tester")
            
            # Create simple Playwright script
            # Use correct backend preview URL
            default_preview_url = f"http://localhost:8001/api/projects/{project_id}/preview/index.html"
            screenshot_script = f"""
import asyncio
from playwright.async_api import async_playwright

async def take_screenshot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            preview_url = "{url}" or "{default_preview_url}"
            await page.goto(preview_url, wait_until="networkidle", timeout=15000)
            await page.wait_for_timeout(2000)
            
            await page.screenshot(path="/tmp/screenshot.png")
            print("✅ Screenshot saved to /tmp/screenshot.png")
        except Exception as e:
            print(f"❌ Screenshot error: {{e}}")
        finally:
            await browser.close()

try:
    asyncio.run(take_screenshot())
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(take_screenshot())
    loop.close()
"""
            
            script_path = workspace_path / ".screenshot.py"
            async with aiofiles.open(script_path, 'w') as f:
                await f.write(screenshot_script)
            
            try:
                env = os.environ.copy()
                env['PATH'] = '/usr/bin:/usr/local/bin:/bin:' + env.get('PATH', '')
                
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, str(script_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                    cwd=workspace_path
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
                stdout_text = stdout.decode() if stdout else ""
                stderr_text = stderr.decode() if stderr else ""
                
                result["output"] = f"📸 Screenshot:\n{stdout_text}\n{stderr_text}"
                await add_log(project_id, "success" if "✅" in stdout_text else "error", "Screenshot genommen", "tester")
            except asyncio.TimeoutError:
                result["output"] = "❌ Screenshot timeout (>30s)"
            except Exception as e:
                result["output"] = f"❌ Screenshot error: {str(e)}"
            
            await update_agent(project_id, "tester", "completed", "Screenshot done")
        
        elif tool_name == "list_files":
            files = []
            for item in workspace_path.rglob("*"):
                if item.is_file() and not any(p in str(item) for p in ['.git', 'node_modules', '__pycache__']):
                    files.append(str(item.relative_to(workspace_path)))
            result["output"] = "Dateien:\n" + "\n".join(files[:50]) if files else "Keine Dateien"
        
        elif tool_name == "run_command":
            command = arguments["command"]
            
            # 🚨 BLOCK FORBIDDEN COMMANDS - npm_env, nodeenv, etc.
            forbidden_patterns = [
                'npm_env', 'nodeenv', 'python.*-m.*nodeenv', 
                'virtualenv.*npm', 'corepack enable',
                'npm_env/bin/', 'venv.*npm'
            ]
            
            import re
            for pattern in forbidden_patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    await add_log(project_id, "error", f"❌ VERBOTENER BEFEHL BLOCKIERT: {command}", "coder")
                    result["output"] = f"""❌ BEFEHL BLOCKIERT!

Der Befehl '{command}' versucht eine isolierte npm-Umgebung zu erstellen.

🚫 VERBOTEN: npm_env, nodeenv, corepack enable

✅ Node.js v20.20.1, npm v10.8.2 und yarn v1.22.22 sind bereits installiert!

NUTZE STATTDESSEN:
  ✅ npm install
  ✅ npm install --prefix client
  ✅ npm install react react-dom
  ✅ npm run build
  ✅ yarn install

BEISPIELE:
  ❌ FALSCH: nodeenv npm_env
  ✅ RICHTIG: npm install

  ❌ FALSCH: npm_env/bin/npm install
  ✅ RICHTIG: npm install

  ❌ FALSCH: corepack enable
  ✅ RICHTIG: npm install (funktioniert direkt!)
"""
                    result["continue"] = True
                    await update_agent(project_id, "coder", "idle", "Blocked forbidden command")
                    return result
            
            # Allow most common development commands
            safe_commands = [
                'npm', 'yarn', 'pip', 'python', 'python3', 'node', 
                'cat', 'ls', 'mkdir', 'echo', 'cd', 'cp', 'mv', 'rm',
                'touch', 'chmod', 'chown', 'find', 'grep', 'head', 'tail',
                'sleep', 'wait', 'curl', 'wget',
                'git', 'docker', 'docker-compose',
                'tar', 'unzip', 'zip',
                'sed', 'awk', 'sort', 'wc', 'diff',
                'which', 'whereis', 'env', 'export', 'set',
                'pwd', 'tree', 'du', 'df',
                'kill', 'ps', 'top',
                'tee', 'xargs',
                'playwright', 'npx', 'pnpm',
            ]
            # Also allow commands that start with ./ or have paths
            is_safe = (
                any(command.strip().startswith(safe) for safe in safe_commands) or
                command.strip().startswith('./') or
                command.strip().startswith('/')
            )
            
            # Block truly dangerous commands
            dangerous_patterns = ['rm -rf /', 'mkfs', 'dd if=', ':(){', 'fork bomb', '> /dev/sd']
            is_dangerous = any(pattern in command for pattern in dangerous_patterns)
            
            if is_dangerous:
                result["output"] = f"✗ Gefährlicher Befehl blockiert: {command}"
            elif not is_safe:
                result["output"] = f"✗ Befehl nicht erlaubt: {command}\n\nErlaubte Befehle: npm, yarn, pip, python, node, git, docker, curl, sleep, cp, mv, rm, find, grep, etc."
            else:
                await add_log(project_id, "info", f"Befehl: {command}", "tester")
                try:
                    # Ensure PATH includes /usr/bin where node is located
                    env = os.environ.copy()
                    env['PATH'] = '/usr/bin:/usr/local/bin:' + env.get('PATH', '')
                    proc = await asyncio.create_subprocess_shell(
                        command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=workspace_path,
                        env=env
                    )
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
                    stdout_text = stdout.decode() if stdout else ""
                    stderr_text = stderr.decode() if stderr else ""
                    output = stdout_text + stderr_text
                    if proc.returncode == 0:
                        await add_log(project_id, "success", f"Befehl erfolgreich: {command}", "tester")
                        result["output"] = f"✓ {command}\n{output[:1000]}"
                    else:
                        await add_log(project_id, "error", f"Befehl fehlgeschlagen: {command}", "tester")
                        result["output"] = f"✗ {command}\nFehler: {output[:1000]}"
                except asyncio.TimeoutError:
                    result["output"] = f"✗ Timeout: {command}"
        
        
        elif tool_name == "build_app":
            """Build React/Vue/Vite app for production"""
            build_command = arguments.get("build_command", "npm run build")
            
            await add_log(project_id, "info", f"📦 Building app: {build_command}", "coder")
            await update_agent(project_id, "coder", "running", f"Building app...")
            
            try:
                # SMART: Auto-detect project directory with package.json
                build_dir = workspace_path
                package_json = workspace_path / "package.json"
                
                if not package_json.exists():
                    # Search for package.json in subdirectories (1 level deep)
                    found = False
                    for subdir in workspace_path.iterdir():
                        if subdir.is_dir() and (subdir / "package.json").exists():
                            build_dir = subdir
                            package_json = subdir / "package.json"
                            found = True
                            await add_log(project_id, "info", f"📂 Projekt gefunden in: {subdir.name}/", "coder")
                            break
                    
                    if not found:
                        result["output"] = "❌ package.json nicht gefunden - weder im Root noch in Unterordnern."
                        await add_log(project_id, "error", "Build failed: No package.json", "coder")
                        await update_agent(project_id, "coder", "idle", "No package.json")
                        return result
                
                # Verify build script exists in package.json
                try:
                    import json as json_mod
                    with open(package_json) as f:
                        pkg = json_mod.load(f)
                    scripts = pkg.get("scripts", {})
                    if "build" not in scripts and build_command == "npm run build":
                        # Try to add a sensible build script
                        if "vite" in str(pkg.get("devDependencies", {})) or "vite" in str(pkg.get("dependencies", {})):
                            scripts["build"] = "vite build"
                        elif "react-scripts" in str(pkg.get("dependencies", {})):
                            scripts["build"] = "react-scripts build"
                        
                        if "build" in scripts:
                            pkg["scripts"] = scripts
                            with open(package_json, 'w') as f:
                                json_mod.dump(pkg, f, indent=2)
                            await add_log(project_id, "info", f"📝 Build-Script automatisch hinzugefügt: {scripts['build']}", "coder")
                except Exception:
                    pass
                
                # Ensure node_modules exist
                if not (build_dir / "node_modules").exists():
                    await add_log(project_id, "info", "📦 Installing dependencies first...", "coder")
                    install_proc = subprocess.run(
                        "npm install",
                        shell=True,
                        cwd=build_dir,
                        capture_output=True,
                        text=True,
                        timeout=300,
                        env={**os.environ, 'PATH': '/usr/bin:/usr/local/bin:' + os.environ.get('PATH', '')}
                    )
                    if install_proc.returncode != 0:
                        result["output"] = f"❌ npm install failed:\n{install_proc.stderr[:500]}"
                        await add_log(project_id, "error", "Dependency installation failed", "coder")
                        return result
                
                # Run build command in the correct directory
                env = os.environ.copy()
                env['PATH'] = '/usr/bin:/usr/local/bin:' + env.get('PATH', '')
                env['CI'] = 'false'  # Disable CI mode warnings
                    
                proc = subprocess.run(
                    build_command,
                    shell=True,
                    cwd=build_dir,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env=env
                )
                
                output = proc.stdout + proc.stderr
                
                if proc.returncode == 0:
                    # Check if build output exists
                    build_output_dirs = ["build", "dist", ".next"]
                    build_found = None
                    for bd in build_output_dirs:
                        if (build_dir / bd).exists():
                            build_found = bd
                            break
                    
                    if build_found:
                        await add_log(project_id, "success", f"✅ Build erfolgreich! Output: {build_found}/", "coder")
                        result["output"] = f"""✅ Build erfolgreich!

Build Output: {build_found}/
Command: {build_command}
Directory: {build_dir.name}/

Preview ist jetzt verfügbar!

{output[:500]}"""
                    else:
                        result["output"] = f"⚠️ Build completed but no build/ or dist/ directory found.\n{output[:500]}"
                else:
                    await add_log(project_id, "error", f"Build failed", "coder")
                    result["output"] = f"❌ Build fehlgeschlagen:\n{output[:800]}"
                
            except subprocess.TimeoutExpired:
                result["output"] = "❌ Build timeout (>5 minutes). Check build configuration."
                await add_log(project_id, "error", "Build timeout", "coder")
            except Exception as e:
                result["output"] = f"❌ Build error: {str(e)}"
                await add_log(project_id, "error", f"Build exception: {str(e)}", "coder")
            
            await update_agent(project_id, "coder", "idle", "Build complete")

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
            max_retries = 3
            min_acceptable_results = 2
            
            await add_log(project_id, "info", f"Web-Suche: {query}", "planner")
            await update_agent(project_id, "planner", "running", f"Recherche: {query}")
            
            all_results = []
            current_query = query
            
            try:
                from ddgs import DDGS
                
                for attempt in range(1, max_retries + 1):
                    await add_log(project_id, "info", f"Suchversuch {attempt}/{max_retries}: {current_query}", "planner")
                    
                    try:
                        results = []
                        with DDGS() as ddgs:
                            for r in ddgs.text(current_query, max_results=max_results):
                                results.append(f"• {r.get('title', '')}\n  {r.get('body', '')[:200]}")
                        
                        if len(results) >= min_acceptable_results:
                            # Success! Found enough results
                            await add_log(project_id, "success", f"✓ Web-Suche erfolgreich: {len(results)} Ergebnisse (Versuch {attempt})", "planner")
                            result["output"] = f"Suchergebnisse für '{current_query}':\n\n" + "\n\n".join(results)
                            break
                        else:
                            # Not enough results, try alternative query
                            all_results.extend(results)
                            await add_log(project_id, "warning", f"⚠️ Nur {len(results)} Ergebnisse gefunden", "planner")
                            
                            if attempt < max_retries:
                                # Generate alternative query using LLM
                                await add_log(project_id, "info", f"🔄 Generiere alternative Suchanfrage...", "planner")
                                await update_agent(project_id, "planner", "running", f"Optimiere Suchanfrage ({attempt}/{max_retries})")
                                
                                current_query = await generate_alternative_query(query, attempt)
                                await add_log(project_id, "info", f"💡 Neue Suchanfrage: {current_query}", "planner")
                            else:
                                # Last attempt failed, return what we have
                                if all_results:
                                    result["output"] = f"Suchergebnisse (nach {max_retries} Versuchen, {len(all_results)} Ergebnisse):\n\n" + "\n\n".join(all_results)
                                    await add_log(project_id, "warning", f"⚠️ Web-Suche: Nur {len(all_results)} Ergebnisse nach {max_retries} Versuchen", "planner")
                                else:
                                    result["output"] = f"Keine ausreichenden Ergebnisse gefunden nach {max_retries} Versuchen.\n\nVersuchte Queries:\n• {query}\n• {current_query}"
                                    await add_log(project_id, "error", f"✗ Web-Suche: Keine Ergebnisse nach {max_retries} Versuchen", "planner")
                    
                    except Exception as search_error:
                        logger.error(f"Search attempt {attempt} failed: {search_error}")
                        if attempt == max_retries:
                            raise
                        # Continue to next attempt
                        await add_log(project_id, "warning", f"⚠️ Suchfehler bei Versuch {attempt}: {str(search_error)}", "planner")
                        
            except Exception as e:
                result["output"] = f"Web-Suche fehlgeschlagen: {str(e)}"
                await add_log(project_id, "error", f"✗ Web-Suche fehlgeschlagen: {str(e)}", "planner")
        
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
        
        elif tool_name == "browser_test":
            test_scenarios = arguments.get("test_scenarios", [])
            preview_url = arguments.get("preview_url", "")
            
            await update_agent(project_id, "tester", "running", "🌐 Browser-Test läuft...")
            await add_log(project_id, "info", f"🌐 Browser-Test startet: {len(test_scenarios)} Szenarien", "tester")
            
            # Use correct backend preview URL
            default_preview_url = f"http://localhost:8001/api/projects/{project_id}/preview/index.html"
            
            # Create test script
            test_script = f"""
import asyncio
import json
import sys
from playwright.async_api import async_playwright

async def run_browser_test():
    test_results = {{
        "passed": [],
        "failed": [],
        "screenshots": []
    }}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"BROWSER: {{msg.text}}"))
        page.on("pageerror", lambda err: print(f"ERROR: {{err}}"))
        
        try:
            # Navigate to preview
            preview_url = "{preview_url}" or "{default_preview_url}"
            await page.goto(preview_url, wait_until="networkidle", timeout=15000)
            await page.wait_for_timeout(2000)
            
            # Take initial screenshot
            await page.screenshot(path="/tmp/browser_test_initial.png")
            test_results["screenshots"].append("/tmp/browser_test_initial.png")
            
            # Check if page is not blank
            body_content = await page.inner_text("body")
            if len(body_content.strip()) > 10:
                test_results["passed"].append("✓ Seite ist nicht leer")
            else:
                test_results["failed"].append("✗ Seite scheint leer zu sein")
            
            # Run test scenarios
            scenarios = {json.dumps(test_scenarios)}
            
            for i, scenario in enumerate(scenarios):
                scenario_lower = scenario.lower()
                
                try:
                    # Scenario: Fill form
                    if "form" in scenario_lower or "formular" in scenario_lower:
                        # Find all input fields
                        inputs = await page.query_selector_all("input:not([type='hidden'])")
                        textareas = await page.query_selector_all("textarea")
                        
                        filled_count = 0
                        for inp in inputs:
                            input_type = await inp.get_attribute("type") or "text"
                            name = await inp.get_attribute("name") or f"field_{{filled_count}}"
                            
                            if input_type in ["text", "email", "tel", "url", "search"]:
                                await inp.fill("Test Input")
                                filled_count += 1
                            elif input_type == "number":
                                await inp.fill("42")
                                filled_count += 1
                            elif input_type == "date":
                                await inp.fill("2024-12-31")
                                filled_count += 1
                        
                        for textarea in textareas:
                            await textarea.fill("Test Textarea Content")
                            filled_count += 1
                        
                        if filled_count > 0:
                            test_results["passed"].append(f"✓ Formular: {{filled_count}} Felder ausgefüllt")
                            
                            # Try to find and click submit button
                            submit_selectors = [
                                "button[type='submit']",
                                "input[type='submit']",
                                "button:has-text('Submit')",
                                "button:has-text('Speichern')",
                                "button:has-text('Senden')",
                                "button:has-text('Save')"
                            ]
                            
                            submitted = False
                            for selector in submit_selectors:
                                try:
                                    submit_btn = await page.query_selector(selector)
                                    if submit_btn:
                                        await submit_btn.click()
                                        await page.wait_for_timeout(1000)
                                        test_results["passed"].append(f"✓ Submit Button geklickt: {{selector}}")
                                        submitted = True
                                        break
                                except:
                                    pass
                            
                            if not submitted:
                                test_results["failed"].append("⚠️ Kein Submit Button gefunden")
                        else:
                            test_results["failed"].append("✗ Keine Formular-Felder gefunden")
                    
                    # Scenario: Click buttons
                    elif "button" in scenario_lower or "click" in scenario_lower:
                        # Search for both <button> elements AND <a> tags styled as buttons
                        # Includes Tailwind-styled buttons (rounded-full, bg-gradient, etc.)
                        buttons = await page.query_selector_all(
                            "button:not([type='submit']), "
                            "a.btn-primary, a.btn-secondary, a.btn, "
                            "a[class*='button'], a[class*='btn'], "
                            "a[class*='rounded-full'], a[class*='bg-gradient'], "
                            "a[class*='rounded-lg'][class*='px-'], "
                            "a[class*='rounded-xl'][class*='px-'], "
                            "[role='button']"
                        )
                        
                        if buttons:
                            for j, btn in enumerate(buttons[:3]):  # Test first 3 buttons
                                btn_text = await btn.inner_text() or f"Button {{j+1}}"
                                try:
                                    await btn.click()
                                    await page.wait_for_timeout(500)
                                    test_results["passed"].append(f"✓ Button geklickt: {{btn_text}}")
                                except Exception as e:
                                    test_results["failed"].append(f"✗ Button-Click fehlgeschlagen: {{btn_text}}")
                        else:
                            test_results["failed"].append("✗ Keine Buttons gefunden")
                    
                    # Scenario: Navigation
                    elif "nav" in scenario_lower or "link" in scenario_lower:
                        # Include BOTH anchor links (#section) AND regular links
                        links = await page.query_selector_all("a[href], nav a, .nav a, [class*='nav'] a")
                        
                        if links:
                            for j, link in enumerate(links[:5]):  # Test first 5 links
                                link_text = await link.inner_text() or f"Link {{j+1}}"
                                link_href = await link.get_attribute("href")
                                
                                if link_href:
                                    try:
                                        await link.click()
                                        await page.wait_for_timeout(500)
                                        test_results["passed"].append(f"✓ Navigation: {{link_text}}")
                                        # Only go back for non-anchor links
                                        if not link_href.startswith("#") and not link_href.startswith("mailto:"):
                                            await page.go_back()
                                    except:
                                        test_results["failed"].append(f"✗ Navigation fehlgeschlagen: {{link_text}}")
                        else:
                            test_results["failed"].append("⚠️ Keine Navigation-Links gefunden")
                    
                    # Generic scenario
                    else:
                        test_results["passed"].append(f"ℹ️ Szenario notiert: {{scenario}}")
                
                except Exception as e:
                    test_results["failed"].append(f"✗ Szenario fehlgeschlagen: {{scenario}} - {{str(e)}}")
            
            # Take final screenshot
            await page.screenshot(path="/tmp/browser_test_final.png")
            test_results["screenshots"].append("/tmp/browser_test_final.png")
            
        except Exception as e:
            test_results["failed"].append(f"✗ Browser-Test Fehler: {{str(e)}}")
        
        finally:
            await browser.close()
    
    # Output results as JSON
    print("BROWSER_TEST_RESULTS_START")
    print(json.dumps(test_results, indent=2))
    print("BROWSER_TEST_RESULTS_END")

if __name__ == "__main__":
    try:
        asyncio.run(run_browser_test())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_browser_test())
        loop.close()
"""
            
            # Write test script
            test_script_path = workspace_path / ".browser_test.py"
            async with aiofiles.open(test_script_path, 'w') as f:
                await f.write(test_script)
            
            # Run test
            try:
                env = os.environ.copy()
                env['PATH'] = '/usr/bin:/usr/local/bin:' + env.get('PATH', '')
                # Use the same Python environment
                python_bin = sys.executable
                
                proc = await asyncio.create_subprocess_exec(
                    python_bin, str(test_script_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                    cwd=workspace_path
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
                output = stdout.decode() if stdout else ""
                error_output = stderr.decode() if stderr else ""
                
                # Parse results
                if "BROWSER_TEST_RESULTS_START" in output:
                    results_str = output.split("BROWSER_TEST_RESULTS_START")[1].split("BROWSER_TEST_RESULTS_END")[0].strip()
                    test_results = json.loads(results_str)
                    
                    passed_count = len(test_results.get("passed", []))
                    failed_count = len(test_results.get("failed", []))
                    
                    result_text = f"🌐 BROWSER-TEST ERGEBNISSE:\n\n"
                    result_text += f"✅ Bestanden: {passed_count}\n"
                    result_text += f"❌ Fehlgeschlagen: {failed_count}\n\n"
                    
                    if test_results.get("passed"):
                        result_text += "ERFOLGE:\n" + "\n".join(test_results["passed"]) + "\n\n"
                    
                    if test_results.get("failed"):
                        result_text += "FEHLER:\n" + "\n".join(test_results["failed"]) + "\n\n"
                        await add_log(project_id, "error", f"Browser-Test: {failed_count} Fehler gefunden", "tester")
                    else:
                        await add_log(project_id, "success", f"Browser-Test: Alle {passed_count} Tests bestanden", "tester")
                    
                    result["output"] = result_text
                    
                    # If tests failed, agent should continue fixing
                    if failed_count > 0:
                        result["continue"] = True
                else:
                    result["output"] = f"⚠️ Browser-Test konnte nicht ausgewertet werden\n\nOutput:\n{output[:2000]}\n\nError:\n{error_output[:2000]}"
                    await add_log(project_id, "warning", "Browser-Test: Auswertung fehlgeschlagen", "tester")
                
            except asyncio.TimeoutError:
                result["output"] = "❌ Browser-Test Timeout (>60s)"
                await add_log(project_id, "error", "Browser-Test: Timeout", "tester")
            except Exception as e:
                result["output"] = f"❌ Browser-Test Fehler: {str(e)}"
                await add_log(project_id, "error", f"Browser-Test: {str(e)}", "tester")
            
            await update_agent(project_id, "tester", "completed", "Browser-Test abgeschlossen")
        
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
        
        elif tool_name == "setup_docker_service":
            service_type = arguments["service_type"]
            service_name = arguments["service_name"]
            port = arguments.get("port")
            custom_config = arguments.get("custom_config")
            
            await update_agent(project_id, "coder", "running", f"Setup {service_type}...")
            await add_log(project_id, "info", f"Richte {service_type} Service ein: {service_name}", "coder")
            
            # Docker Compose Templates
            templates = {
                "mongodb": {
                    "image": "mongo:latest",
                    "ports": [f"{port or 27017}:27017"],
                    "environment": {
                        "MONGO_INITDB_ROOT_USERNAME": "admin",
                        "MONGO_INITDB_ROOT_PASSWORD": "password"
                    },
                    "volumes": [f"{service_name}_data:/data/db"]
                },
                "postgresql": {
                    "image": "postgres:latest",
                    "ports": [f"{port or 5432}:5432"],
                    "environment": {
                        "POSTGRES_USER": "admin",
                        "POSTGRES_PASSWORD": "password",
                        "POSTGRES_DB": "database"
                    },
                    "volumes": [f"{service_name}_data:/var/lib/postgresql/data"]
                },
                "mysql": {
                    "image": "mysql:latest",
                    "ports": [f"{port or 3306}:3306"],
                    "environment": {
                        "MYSQL_ROOT_PASSWORD": "password",
                        "MYSQL_DATABASE": "database"
                    },
                    "volumes": [f"{service_name}_data:/var/lib/mysql"]
                },
                "redis": {
                    "image": "redis:latest",
                    "ports": [f"{port or 6379}:6379"],
                    "volumes": [f"{service_name}_data:/data"]
                },
                "elasticsearch": {
                    "image": "elasticsearch:8.11.0",
                    "ports": [f"{port or 9200}:9200"],
                    "environment": {
                        "discovery.type": "single-node",
                        "xpack.security.enabled": "false"
                    },
                    "volumes": [f"{service_name}_data:/usr/share/elasticsearch/data"]
                },
                "rabbitmq": {
                    "image": "rabbitmq:management",
                    "ports": [f"{port or 5672}:5672", "15672:15672"],
                    "volumes": [f"{service_name}_data:/var/lib/rabbitmq"]
                }
            }
            
            # Get template or use custom
            service_config = custom_config if custom_config else templates.get(service_type, {})
            
            # Create docker-compose.yml
            docker_compose = {
                "version": "3.8",
                "services": {
                    service_name: service_config
                },
                "volumes": {
                    f"{service_name}_data": {}
                }
            }
            
            # Write docker-compose.yml
            compose_path = workspace_path / "docker-compose.yml"
            import yaml
            with open(compose_path, 'w') as f:
                yaml.dump(docker_compose, f, default_flow_style=False)
            
            await add_log(project_id, "success", f"docker-compose.yml erstellt", "coder")
            
            # START THE SERVICE AUTOMATICALLY!
            try:
                await add_log(project_id, "info", f"Starte {service_type} Container...", "coder")
                
                # docker-compose up -d
                proc = subprocess.run(
                    ["docker-compose", "up", "-d"],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if proc.returncode == 0:
                    await add_log(project_id, "success", f"✅ {service_type} läuft auf Port {port or 'default'}", "coder")
                    
                    # Connection info
                    connection_info = {
                        "mongodb": f"mongodb://admin:password@localhost:{port or 27017}/database",
                        "postgresql": f"postgresql://admin:password@localhost:{port or 5432}/database",
                        "mysql": f"mysql://root:password@localhost:{port or 3306}/database",
                        "redis": f"redis://localhost:{port or 6379}",
                    }.get(service_type, f"Service running on port {port}")
                    
                    result["output"] = f"""✅ {service_type} Service gestartet!

Service: {service_name}
Port: {port or 'default'}
Status: Running

Connection String:
{connection_info}

⏳ Warte 5 Sekunden bis Service bereit ist:
   run_command("sleep 5")

Dann kannst du die App starten!"""
                else:
                    result["output"] = f"⚠️ docker-compose.yml erstellt, aber Start fehlgeschlagen:\n{proc.stderr[:500]}\n\nManuel starten: docker-compose up -d"
            except Exception as e:
                result["output"] = f"✓ docker-compose.yml erstellt\n⚠️ Auto-Start fehlgeschlagen: {str(e)}\nManuel starten: docker-compose up -d"
            
            await update_agent(project_id, "coder", "completed", "Service Setup complete")
        
        elif tool_name == "install_package":
            package_manager = arguments["package_manager"]
            package_name = arguments["package_name"]
            save_dev = arguments.get("save_dev", False)
            
            await update_agent(project_id, "coder", "running", f"Installiere {package_name}...")
            await add_log(project_id, "info", f"Installiere Paket: {package_name} ({package_manager})", "coder")
            
            try:
                env = os.environ.copy()
                env['PATH'] = '/usr/bin:/usr/local/bin:/bin:' + env.get('PATH', '')
                
                # SMART: Auto-detect correct install directory
                install_dir = workspace_path
                
                # Ensure package.json exists for npm/yarn
                if package_manager in ["npm", "yarn"]:
                    package_json_path = workspace_path / "package.json"
                    if not package_json_path.exists():
                        # Search for package.json in subdirectories (1 level deep)
                        found_subdir = False
                        for subdir in workspace_path.iterdir():
                            if subdir.is_dir() and (subdir / "package.json").exists():
                                install_dir = subdir
                                package_json_path = subdir / "package.json"
                                found_subdir = True
                                await add_log(project_id, "info", f"📂 package.json gefunden in: {subdir.name}/", "coder")
                                break
                        
                        if not found_subdir:
                            await add_log(project_id, "info", "Erstelle package.json...", "coder")
                            default_package_json = {
                                "name": "project",
                                "version": "1.0.0",
                                "description": "",
                                "main": "index.js",
                                "scripts": {
                                    "start": "node index.js"
                                },
                                "dependencies": {},
                                "devDependencies": {}
                            }
                            async with aiofiles.open(package_json_path, 'w') as f:
                                await f.write(json.dumps(default_package_json, indent=2))
                    else:
                        install_dir = workspace_path
                
                if package_manager == "npm":
                    cmd = f"npm install {package_name}"
                    if save_dev:
                        cmd += " --save-dev"
                elif package_manager == "yarn":
                    cmd = f"yarn add {package_name}"
                    if save_dev:
                        cmd += " --dev"
                elif package_manager == "pip":
                    cmd = f"pip install {package_name}"
                
                proc = subprocess.run(cmd, shell=True, cwd=install_dir, capture_output=True, text=True, timeout=120, env=env)
                
                if proc.returncode == 0:
                    result["output"] = f"✓ Paket installiert: {package_name}\n{proc.stdout[:500]}"
                    await add_log(project_id, "success", f"Paket installiert: {package_name}", "coder")
                else:
                    error_output = proc.stderr[:500]
                    # Better error message
                    if "ENOENT" in error_output or "No such file" in error_output:
                        result["output"] = f"✗ Installation fehlgeschlagen: {package_name}\nFehler: Node.js/npm nicht im PATH oder Workspace-Problem\n\nDetails:\n{error_output}\n\nTipp: Nutze run_command statt install_package für mehr Kontrolle"
                    else:
                        result["output"] = f"✗ Installation fehlgeschlagen: {package_name}\n{error_output}"
                    await add_log(project_id, "error", f"Installation fehlgeschlagen: {package_name}", "coder")
                
                await update_agent(project_id, "coder", "completed", "Package installed")
            except subprocess.TimeoutExpired:
                result["output"] = f"✗ Timeout bei Installation: {package_name}"
                await add_log(project_id, "error", f"Timeout: {package_name}", "coder")
                await update_agent(project_id, "coder", "idle", "Timeout")
            except Exception as e:
                result["output"] = f"✗ Fehler: {str(e)}"
                await add_log(project_id, "error", f"Fehler: {str(e)}", "coder")
                await update_agent(project_id, "coder", "idle", "Error")
        
        elif tool_name == "troubleshoot":
            problem = arguments["problem"]
            attempted_solutions = arguments.get("attempted_solutions", [])
            
            await update_agent(project_id, "debugger", "running", "Troubleshooting...")
            await add_log(project_id, "info", f"🔧 Troubleshooting: {problem}", "debugger")
            
            # Simulate troubleshoot agent analysis
            analysis = f"""🔧 TROUBLESHOOT ANALYSIS

PROBLEM: {problem}

ATTEMPTED SOLUTIONS:
""" + "\n".join(f"  {i+1}. {sol}" for i, sol in enumerate(attempted_solutions))
            
            analysis += """

ROOT CAUSE ANALYSIS:
✓ Check if files exist in workspace
✓ Verify all dependencies installed
✓ Check for typos in code
✓ Review error messages carefully

ALTERNATIVE SOLUTIONS:
1. Try a different approach:
   - If npm install fails → use run_command("yarn install")
   - If browser_test fails → check console errors first
   
2. Simplify the problem:
   - Break down into smaller steps
   - Test each part individually
   
3. Check environment:
   - Are all tools available? (node, npm, python)
   - Is the workspace path correct?
   
4. Review recent changes:
   - What was the last working state?
   - What changed since then?

RECOMMENDED NEXT STEPS:
→ Start with simplest solution first
→ Test after each change
→ If still stuck, try completely different approach

DEBUGGING COMMANDS:
• run_command("ls -la") - Check workspace
• read_file("package.json") - Verify config
• run_command("npm --version") - Check tools
"""
            
            result["output"] = analysis
            await add_log(project_id, "success", "Troubleshoot-Analyse abgeschlossen", "debugger")
            await update_agent(project_id, "debugger", "completed", "Analysis done")
        
        elif tool_name == "get_integration_playbook":
            integration = arguments["integration"]
            use_case = arguments.get("use_case", "")
            
            await update_agent(project_id, "planner", "running", f"Integration: {integration}")
            await add_log(project_id, "info", f"📚 Integration Playbook: {integration}", "planner")
            
            # Simulate integration expert
            playbook = f"""📚 INTEGRATION PLAYBOOK: {integration}

USE CASE: {use_case or "General integration"}

"""
            
            # Provide specific playbooks based on integration
            if "openai" in integration.lower() or "gpt" in integration.lower():
                playbook += """OPENAI GPT INTEGRATION:

1. INSTALLATION:
   run_command("pip install openai")

2. CODE EXAMPLE:
   ```python
   from openai import OpenAI
   client = OpenAI(api_key="your-api-key")
   
   response = client.chat.completions.create(
       model="gpt-4",
       messages=[{"role": "user", "content": "Hello!"}]
   )
   print(response.choices[0].message.content)
   ```

3. BEST PRACTICES:
   ✓ Store API key in .env file
   ✓ Use try-except for error handling
   ✓ Implement rate limiting
   ✓ Stream responses for better UX

4. COMMON ISSUES:
   • Rate limits → Add delays between calls
   • Timeouts → Increase timeout parameter
   • Invalid key → Check API key format
"""
            elif "stripe" in integration.lower():
                playbook += """STRIPE PAYMENT INTEGRATION:

1. INSTALLATION:
   run_command("pip install stripe")  # Backend
   run_command("npm install @stripe/stripe-js")  # Frontend

2. CODE EXAMPLE (Backend):
   ```python
   import stripe
   stripe.api_key = "sk_test_..."
   
   payment_intent = stripe.PaymentIntent.create(
       amount=1000,
       currency="usd"
   )
   ```

3. BEST PRACTICES:
   ✓ Use test keys in development
   ✓ Implement webhooks for payment confirmation
   ✓ Handle errors gracefully
   ✓ PCI compliance for card data

4. TESTING:
   • Use test card: 4242 4242 4242 4242
"""
            elif "mongodb" in integration.lower():
                playbook += """MONGODB INTEGRATION:

1. INSTALLATION:
   run_command("pip install pymongo motor")  # Python
   run_command("npm install mongodb")  # Node.js

2. CODE EXAMPLE:
   ```python
   from motor.motor_asyncio import AsyncIOMotorClient
   
   client = AsyncIOMotorClient("mongodb://localhost:27017")
   db = client.database_name
   
   # Insert
   await db.users.insert_one({"name": "John"})
   
   # Find
   user = await db.users.find_one({"name": "John"})
   ```

3. BEST PRACTICES:
   ✓ Use indexes for performance
   ✓ Validate data with schemas
   ✓ Handle connection errors
   ✓ Close connections properly
"""
            else:
                playbook += f"""GENERAL INTEGRATION GUIDE:

1. RESEARCH:
   • web_search("{integration} best practices")
   • web_search("{integration} code examples")

2. SETUP:
   • Install required packages
   • Configure API keys/credentials
   • Set up environment variables

3. IMPLEMENTATION:
   • Start with simple example
   • Test each feature separately
   • Add error handling
   • Follow official documentation

4. TESTING:
   • Use test/sandbox environment
   • Verify all edge cases
   • Check error scenarios
"""
            
            result["output"] = playbook
            await add_log(project_id, "success", f"Integration Playbook: {integration}", "planner")
            await update_agent(project_id, "planner", "completed", "Playbook ready")
        
        elif tool_name == "get_design_guidelines":
            app_type = arguments["app_type"].lower()
            style = arguments.get("style", "modern")
            
            await update_agent(project_id, "planner", "running", "Design Guidelines...")
            await add_log(project_id, "info", f"🎨 Design Guidelines: {app_type} ({style})", "planner")
            
            # ═══════════════════════════════════════════════════════════════
            # BRANCHEN-TEMPLATES mit Tailwind CSS
            # ═══════════════════════════════════════════════════════════════
            
            industry_templates = {
                "auto": {
                    "name": "Auto / Werkstatt / Tuning",
                    "colors": "bg-gray-950 text-white, accent: from-red-600 to-orange-500",
                    "tailwind_bg": "bg-gray-950",
                    "accent_gradient": "from-red-600 to-orange-500",
                    "accent_text": "text-red-500",
                    "fonts": "font-display für Headlines (Playfair Display), font-sans für Body (Inter)",
                    "emotion": "Kraft, Power, Geschwindigkeit, Adrenalin",
                    "images": [
                        "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=1920&h=1080&fit=crop",
                        "https://images.unsplash.com/photo-1544636331-e26879cd4d9b?w=800&h=600&fit=crop",
                        "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=800&h=600&fit=crop",
                        "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=800&h=600&fit=crop",
                        "https://images.unsplash.com/photo-1494976388531-d1058494cdd8?w=1920&h=1080&fit=crop",
                    ],
                    "copy_style": "Kraftvoll, direkt, maskulin. 'Entfesseln Sie die volle Power', 'Performance auf höchstem Niveau', 'Ihr Fahrzeug verdient das Beste'",
                    "stats": ["15+ Jahre Erfahrung", "2000+ PS freigesetzt", "500+ zufriedene Fahrer", "98% Weiterempfehlung"],
                },
                "restaurant": {
                    "name": "Restaurant / Gastronomie / Café",
                    "colors": "bg-stone-950 text-white, accent: from-amber-600 to-yellow-500",
                    "tailwind_bg": "bg-stone-950",
                    "accent_gradient": "from-amber-600 to-yellow-500",
                    "accent_text": "text-amber-500",
                    "emotion": "Genuss, Wärme, Gemütlichkeit, Kulinarik",
                    "images": [
                        "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1920&h=1080&fit=crop",
                        "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&h=600&fit=crop",
                        "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800&h=600&fit=crop",
                        "https://images.unsplash.com/photo-1551218808-94e220e084d2?w=800&h=600&fit=crop",
                    ],
                    "copy_style": "Sinnlich, einladend. 'Kulinarische Meisterwerke', 'Wo jeder Bissen eine Geschichte erzählt', 'Genuss neu definiert'",
                    "stats": ["10+ Jahre Tradition", "50.000+ Gäste", "4.9★ Bewertung", "100% frische Zutaten"],
                },
                "fitness": {
                    "name": "Fitness / Gym / Personal Training",
                    "colors": "bg-zinc-950 text-white, accent: from-lime-500 to-emerald-500",
                    "tailwind_bg": "bg-zinc-950",
                    "accent_gradient": "from-lime-500 to-emerald-500",
                    "accent_text": "text-lime-400",
                    "emotion": "Motivation, Stärke, Transformation, Energie",
                    "images": [
                        "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1920&h=1080&fit=crop",
                        "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=800&h=600&fit=crop",
                        "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=800&h=600&fit=crop",
                        "https://images.unsplash.com/photo-1549060279-7e168fcee0c2?w=800&h=600&fit=crop",
                    ],
                    "copy_style": "Motivierend, energisch. 'Dein stärkstes Ich', 'Grenzen existieren nur im Kopf', 'Transformiere deinen Körper'",
                    "stats": ["5000+ transformierte Körper", "12+ Jahre Erfahrung", "98% Zielerreichung", "24/7 Support"],
                },
                "tech": {
                    "name": "Technologie / Software / SaaS",
                    "colors": "bg-slate-950 text-white, accent: from-blue-500 to-cyan-400",
                    "tailwind_bg": "bg-slate-950",
                    "accent_gradient": "from-blue-500 to-cyan-400",
                    "accent_text": "text-blue-400",
                    "emotion": "Innovation, Zukunft, Effizienz, Vertrauen",
                    "images": [
                        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1920&h=1080&fit=crop",
                        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=800&h=600&fit=crop",
                        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&h=600&fit=crop",
                        "https://images.unsplash.com/photo-1504639725590-34d0984388bd?w=800&h=600&fit=crop",
                    ],
                    "copy_style": "Klar, modern, zukunftsorientiert. 'Die Zukunft beginnt hier', 'Technologie die begeistert', 'Innovation trifft Einfachheit'",
                    "stats": ["99.9% Uptime", "10M+ Nutzer", "50+ Integrationen", "ISO 27001 zertifiziert"],
                },
                "immobilien": {
                    "name": "Immobilien / Makler / Real Estate",
                    "colors": "bg-neutral-950 text-white, accent: from-emerald-600 to-teal-500",
                    "tailwind_bg": "bg-neutral-950",
                    "accent_gradient": "from-emerald-600 to-teal-500",
                    "accent_text": "text-emerald-400",
                    "emotion": "Vertrauen, Zuhause, Geborgenheit, Luxus",
                    "images": [
                        "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=1920&h=1080&fit=crop",
                        "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&h=600&fit=crop",
                        "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&h=600&fit=crop",
                        "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800&h=600&fit=crop",
                    ],
                    "copy_style": "Vertrauensvoll, premium. 'Ihr Traumzuhause wartet', 'Wo Zuhause beginnt', 'Premium Immobilien, persönliche Beratung'",
                    "stats": ["500+ vermittelte Objekte", "20+ Jahre Marktkenntnis", "4.8★ Kundenbewertung", "Ø 30 Tage bis Verkauf"],
                },
                "anwalt": {
                    "name": "Anwalt / Kanzlei / Recht",
                    "colors": "bg-slate-950 text-white, accent: from-amber-500 to-yellow-400",
                    "tailwind_bg": "bg-slate-950",
                    "accent_gradient": "from-amber-500 to-yellow-400",
                    "accent_text": "text-amber-400",
                    "emotion": "Vertrauen, Kompetenz, Autorität, Sicherheit",
                    "images": [
                        "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=1920&h=1080&fit=crop",
                        "https://images.unsplash.com/photo-1505664194779-8beaceb93744?w=800&h=600&fit=crop",
                        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&h=600&fit=crop",
                    ],
                    "copy_style": "Seriös, kompetent. 'Ihr Recht in besten Händen', 'Kompetenz die überzeugt', 'Wir kämpfen für Ihre Interessen'",
                    "stats": ["2000+ gewonnene Fälle", "30+ Jahre Erfahrung", "100% Diskretion", "Erstberatung kostenlos"],
                },
                "beauty": {
                    "name": "Beauty / Kosmetik / Friseur / Spa",
                    "colors": "bg-stone-950 text-white, accent: from-rose-500 to-pink-400",
                    "tailwind_bg": "bg-stone-950",
                    "accent_gradient": "from-rose-500 to-pink-400",
                    "accent_text": "text-rose-400",
                    "emotion": "Eleganz, Schönheit, Entspannung, Verwöhnung",
                    "images": [
                        "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=1920&h=1080&fit=crop",
                        "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=800&h=600&fit=crop",
                        "https://images.unsplash.com/photo-1487412947147-5cebf100ffc2?w=800&h=600&fit=crop",
                    ],
                    "copy_style": "Elegant, verwöhnend. 'Schönheit neu erleben', 'Ihr Moment der Entspannung', 'Wo Pflege zur Kunst wird'",
                    "stats": ["5000+ zufriedene Kundinnen", "15+ Jahre Expertise", "100% Naturprodukte", "4.9★ Google Bewertung"],
                },
                "handwerk": {
                    "name": "Handwerk / Bau / Elektriker / Sanitär",
                    "colors": "bg-zinc-950 text-white, accent: from-yellow-500 to-amber-500",
                    "tailwind_bg": "bg-zinc-950",
                    "accent_gradient": "from-yellow-500 to-amber-500",
                    "accent_text": "text-yellow-400",
                    "emotion": "Zuverlässigkeit, Qualität, Handwerk, Vertrauen",
                    "images": [
                        "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=1920&h=1080&fit=crop",
                        "https://images.unsplash.com/photo-1581578731548-c64695cc6952?w=800&h=600&fit=crop",
                        "https://images.unsplash.com/photo-1621905252507-b35492cc74b4?w=800&h=600&fit=crop",
                    ],
                    "copy_style": "Bodenständig, zuverlässig. 'Qualität die man sieht', 'Ihr Meisterbetrieb vor Ort', 'Handwerk mit Leidenschaft'",
                    "stats": ["25+ Jahre Meisterbetrieb", "3000+ Projekte", "Festpreisgarantie", "24h Notdienst"],
                },
                "medizin": {
                    "name": "Medizin / Arztpraxis / Gesundheit",
                    "colors": "bg-slate-950 text-white, accent: from-teal-500 to-cyan-400",
                    "tailwind_bg": "bg-slate-950",
                    "accent_gradient": "from-teal-500 to-cyan-400",
                    "accent_text": "text-teal-400",
                    "emotion": "Vertrauen, Fürsorge, Kompetenz, Gesundheit",
                    "images": [
                        "https://images.unsplash.com/photo-1505751172876-fa1923c5c528?w=1920&h=1080&fit=crop",
                        "https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=800&h=600&fit=crop",
                        "https://images.unsplash.com/photo-1551190822-a9ce113d0d15?w=800&h=600&fit=crop",
                    ],
                    "copy_style": "Vertrauensvoll, fürsorglich. 'Ihre Gesundheit in besten Händen', 'Modernste Medizin, persönliche Betreuung'",
                    "stats": ["20+ Jahre Praxiserfahrung", "10.000+ Patienten", "Modernste Technik", "Kurze Wartezeiten"],
                },
                "ecommerce": {
                    "name": "E-Commerce / Online-Shop",
                    "colors": "bg-white text-gray-900, accent: from-indigo-600 to-purple-600",
                    "tailwind_bg": "bg-gray-50",
                    "accent_gradient": "from-indigo-600 to-purple-600",
                    "accent_text": "text-indigo-600",
                    "emotion": "Vertrauen, Entdeckung, Shopping-Erlebnis",
                    "images": [
                        "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1920&h=1080&fit=crop",
                        "https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=800&h=600&fit=crop",
                        "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=800&h=600&fit=crop",
                    ],
                    "copy_style": "Einladend, überzeugend. 'Entdecke was du liebst', 'Kostenloser Versand ab 50€', 'Über 10.000 zufriedene Kunden'",
                    "stats": ["10.000+ Produkte", "Kostenloser Versand", "30 Tage Rückgabe", "4.8★ Trustpilot"],
                },
            }
            
            # Detect industry from app_type and style
            detected_industry = None
            proj_desc = ""
            try:
                proj_data = await db.projects.find_one({"id": project_id})
                if proj_data:
                    proj_desc = proj_data.get('description', '')
            except:
                pass
            search_terms = (app_type + " " + style + " " + proj_desc).lower()
            
            for key, template in industry_templates.items():
                keywords = key.split("/") + template["name"].lower().split("/")
                for kw in keywords:
                    if kw.strip() in search_terms:
                        detected_industry = key
                        break
                if detected_industry:
                    break
            
            # Additional keyword matching
            keyword_map = {
                "auto": ["auto", "werkstatt", "tuning", "kfz", "motor", "leistung", "fahrzeug", "car", "garage", "reifen"],
                "restaurant": ["restaurant", "cafe", "café", "essen", "food", "küche", "gastronomie", "bistro", "bar", "catering"],
                "fitness": ["fitness", "gym", "sport", "training", "personal", "workout", "yoga", "crossfit", "bodybuilding"],
                "tech": ["tech", "software", "saas", "app", "digital", "startup", "it", "cloud", "ai", "web"],
                "immobilien": ["immobilien", "makler", "wohnung", "haus", "real estate", "property", "miete"],
                "anwalt": ["anwalt", "kanzlei", "recht", "jurist", "law", "rechtsanwalt", "notar"],
                "beauty": ["beauty", "kosmetik", "friseur", "spa", "wellness", "nail", "haar", "salon", "pflege"],
                "handwerk": ["handwerk", "bau", "elektrik", "sanitär", "dachdecker", "maler", "tischler", "schreiner", "meister"],
                "medizin": ["arzt", "praxis", "medizin", "gesundheit", "zahnarzt", "therapeut", "physio", "klinik", "doctor"],
                "ecommerce": ["shop", "ecommerce", "e-commerce", "online-shop", "store", "produkt", "kaufen"],
            }
            
            if not detected_industry:
                for key, keywords in keyword_map.items():
                    for kw in keywords:
                        if kw in search_terms:
                            detected_industry = key
                            break
                    if detected_industry:
                        break
            
            # Default to tech if nothing detected
            if not detected_industry:
                detected_industry = "tech"
            
            tmpl = industry_templates[detected_industry]
            
            guidelines = f"""🎨 PROFESSIONELLE DESIGN GUIDELINES — TAILWIND CSS

═══ BRANCHE: {tmpl['name']} ═══
EMOTION: {tmpl['emotion']}
FARBSCHEMA: {tmpl['colors']}

═══ TAILWIND KONFIGURATION (im <head>!) ═══
```html
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Playfair+Display:wght@400;500;600;700;900&display=swap" rel="stylesheet">
<script>
tailwind.config = {{
  theme: {{
    extend: {{
      fontFamily: {{
        'sans': ['Inter', 'sans-serif'],
        'display': ['Playfair Display', 'serif'],
      }}
    }}
  }}
}}
</script>
```

═══ BILDER (Unsplash - NUTZE DIESE!) ═══
Hero:    {tmpl['images'][0]}
Bild 2:  {tmpl['images'][1] if len(tmpl['images']) > 1 else 'N/A'}
Bild 3:  {tmpl['images'][2] if len(tmpl['images']) > 2 else 'N/A'}
Bild 4:  {tmpl['images'][3] if len(tmpl['images']) > 3 else 'N/A'}

═══ STATISTIK-ZAHLEN ═══
{chr(10).join(f'• {s}' for s in tmpl['stats'])}

═══ COPYWRITING-STIL ═══
{tmpl['copy_style']}

═══ PFLICHT TAILWIND-KLASSEN ═══

NAVIGATION:
<nav id="navbar" class="fixed top-0 w-full z-50 transition-all duration-500 py-5">
  <div class="max-w-7xl mx-auto px-6 flex justify-between items-center">
    <a class="font-display text-2xl font-bold text-white">Brand</a>
    <div class="hidden md:flex gap-8">
      <a class="text-white/70 hover:text-white transition text-sm tracking-wide">Link</a>
    </div>
  </div>
</nav>
nav.scrolled → Tailwind: Nutze JS um bg-gray-950/95 backdrop-blur-xl py-3 shadow-2xl zu togglen

HERO SECTION:
class="relative min-h-screen flex items-center justify-center text-white text-center"
style="background: linear-gradient(135deg, rgba(0,0,0,0.7), rgba(0,0,0,0.4)), url('{tmpl['images'][0]}') center/cover"
H1: class="font-display text-5xl md:text-7xl font-bold tracking-tight leading-tight"
P: class="text-lg md:text-xl text-white/80 mt-6 max-w-2xl mx-auto"
CTA: class="px-8 py-4 bg-gradient-to-r {tmpl['accent_gradient']} rounded-full font-semibold shadow-lg hover:-translate-y-1 transition-all"

KARTEN:
class="bg-white/5 border border-white/10 rounded-2xl p-8 hover-lift"
oder dark: class="bg-gray-900/50 backdrop-blur border border-gray-800 rounded-2xl p-8 hover-lift"

STATISTIKEN:
class="grid grid-cols-2 md:grid-cols-4 gap-8 text-center py-20"
Zahl: class="text-4xl md:text-5xl font-bold"
Label: class="text-sm text-white/60 mt-2 uppercase tracking-wider"

GALERIE:
class="grid grid-cols-1 md:grid-cols-3 gap-6"
Bild-Container: class="relative overflow-hidden rounded-xl aspect-[4/3] img-zoom"
Bild: class="w-full h-full object-cover"

TESTIMONIALS:
class="bg-white/5 rounded-2xl p-8 border border-white/10"
Sterne: ★★★★★ in {tmpl['accent_text']}
Name: class="font-semibold mt-4"

CTA SECTION:
class="py-24 bg-gradient-to-r {tmpl['accent_gradient']}"
H2: class="font-display text-4xl md:text-5xl font-bold text-white text-center"

FOOTER:
class="{tmpl['tailwind_bg']} border-t border-white/10 py-12"

═══ PFLICHT CUSTOM CSS (in <style>) ═══
.reveal {{ opacity: 0; transform: translateY(40px); transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1); }}
.reveal.active {{ opacity: 1; transform: translateY(0); }}
.hover-lift {{ transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.4s ease; }}
.hover-lift:hover {{ transform: translateY(-10px); box-shadow: 0 25px 60px rgba(0,0,0,0.25); }}
.img-zoom img {{ transition: transform 0.6s ease; }}
.img-zoom:hover img {{ transform: scale(1.08); }}
nav.scrolled {{ background: rgba(10,10,10,0.95); backdrop-filter: blur(20px); padding-top: 0.75rem; padding-bottom: 0.75rem; box-shadow: 0 4px 30px rgba(0,0,0,0.3); }}

═══ PFLICHT JAVASCRIPT ═══
// IntersectionObserver for reveal animations
const observer = new IntersectionObserver((entries) => {{
  entries.forEach(e => {{ if(e.isIntersecting) e.target.classList.add('active'); }});
}}, {{ threshold: 0.1 }});
document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

// Nav scroll effect
window.addEventListener('scroll', () => {{
  document.querySelector('nav')?.classList.toggle('scrolled', window.scrollY > 50);
}});

// Smooth scroll
document.querySelectorAll('a[href^="#"]').forEach(a => {{
  a.addEventListener('click', e => {{
    e.preventDefault();
    document.querySelector(a.getAttribute('href'))?.scrollIntoView({{ behavior: 'smooth' }});
  }});
}});

// Counter animation
document.querySelectorAll('[data-count]').forEach(el => {{
  new IntersectionObserver((entries) => {{
    if(entries[0].isIntersecting) {{
      const target = parseInt(el.dataset.count);
      let current = 0;
      const timer = setInterval(() => {{
        current += target/60;
        if(current >= target) {{ el.textContent = target + (el.dataset.suffix||''); clearInterval(timer); }}
        else el.textContent = Math.floor(current) + (el.dataset.suffix||'');
      }}, 16);
    }}
  }}, {{ threshold: 0.5 }}).observe(el);
}});
"""
            
            result["output"] = guidelines
            await add_log(project_id, "success", f"Professionelle Design Guidelines erstellt ({tmpl['name']})", "planner")
            await update_agent(project_id, "planner", "completed", "Guidelines ready")
        
        elif tool_name == "advanced_test":
            test_type = arguments["test_type"]
            test_scenarios = arguments.get("test_scenarios", [])
            
            await update_agent(project_id, "tester", "running", f"Advanced Testing: {test_type}")
            await add_log(project_id, "info", f"🧪 Advanced Test: {test_type}", "tester")
            
            # For now, delegate to browser_test or provide detailed analysis
            if test_type in ["ui", "both"]:
                # Call browser_test internally
                browser_result = await execute_tool("browser_test", {"test_scenarios": test_scenarios}, workspace_path, project_id)
                result["output"] = f"🧪 ADVANCED UI TEST\n\n{browser_result['output']}"
            else:
                result["output"] = f"""🧪 ADVANCED BACKEND TEST

TEST SCENARIOS:
""" + "\n".join(f"  • {scenario}" for scenario in test_scenarios) + """

RECOMMENDED TESTS:
1. API Endpoints:
   • Test all routes with curl
   • Verify status codes (200, 404, 500)
   • Check response format (JSON)
   • Test authentication

2. Database:
   • Verify CRUD operations
   • Check data persistence
   • Test query performance
   • Validate indexes

3. Error Handling:
   • Invalid inputs
   • Missing data
   • Network errors
   • Edge cases

4. Performance:
   • Response times
   • Concurrent requests
   • Memory usage
   • Database queries

Use run_command to execute curl tests:
run_command("curl -X GET http://localhost:8000/api/endpoint")
"""
            
            await add_log(project_id, "success", "Advanced Test abgeschlossen", "tester")
            await update_agent(project_id, "tester", "completed", "Testing done")
        
        elif tool_name == "think":
            thought = arguments["thought"]
            
            # Log as special "thought" type
            await add_log(project_id, "info", f"💭 Gedanke: {thought}", "orchestrator")
            result["output"] = f"💭 Logged thought: {thought[:100]}..."
            # Don't change agent status for thoughts
        
        elif tool_name == "code_review":
            files_to_review = arguments.get("files_to_review", [])
            
            await update_agent(project_id, "reviewer", "running", "Code Review...")
            await add_log(project_id, "info", "📝 Code Review startet", "reviewer")
            
            if not files_to_review:
                # Review all files in workspace
                all_files = []
                for file in workspace_path.rglob("*"):
                    if file.is_file() and not any(part.startswith('.') for part in file.parts):
                        all_files.append(str(file.relative_to(workspace_path)))
                files_to_review = all_files[:10]  # Review max 10 files
            
            review_results = []
            issues_found = 0
            
            for file_path in files_to_review:
                full_path = workspace_path / file_path
                if not full_path.exists():
                    continue
                
                try:
                    async with aiofiles.open(full_path, 'r') as f:
                        content = await f.read()
                    
                    file_issues = []
                    
                    # Check for common issues
                    if "TODO" in content or "FIXME" in content:
                        file_issues.append("⚠️ Contains TODO/FIXME comments")
                    
                    if "console.log" in content and file_path.endswith('.js'):
                        file_issues.append("⚠️ Contains console.log (remove for production)")
                    
                    if "debugger" in content:
                        file_issues.append("⚠️ Contains debugger statement")
                    
                    if len(content) > 10000:
                        file_issues.append("ℹ️ Large file (>10KB) - consider splitting")
                    
                    if file_issues:
                        issues_found += len(file_issues)
                        review_results.append(f"\n{file_path}:\n  " + "\n  ".join(file_issues))
                    else:
                        review_results.append(f"\n{file_path}: ✓ Looks good")
                
                except Exception as e:
                    review_results.append(f"\n{file_path}: ⚠️ Could not review - {str(e)}")
            
            review_output = f"""📝 CODE REVIEW RESULTS

FILES REVIEWED: {len(files_to_review)}
ISSUES FOUND: {issues_found}

REVIEW:
""" + "\n".join(review_results)
            
            if issues_found > 0:
                review_output += f"""

⚠️ RECOMMENDATION: Fix these issues before mark_complete
"""
                await add_log(project_id, "warning", f"Code Review: {issues_found} Probleme gefunden", "reviewer")
            else:
                review_output += "\n\n✅ CODE QUALITY: Good!"
                await add_log(project_id, "success", "Code Review: Keine Probleme", "reviewer")
            
            result["output"] = review_output
            await update_agent(project_id, "reviewer", "completed", "Review done")
        
        elif tool_name == "update_memory":
            memory_type = arguments["memory_type"]
            content = arguments["content"]
            
            # Create memory directory if not exists
            memory_dir = workspace_path / "memory"
            memory_dir.mkdir(exist_ok=True)
            
            memory_file = memory_dir / f"{memory_type}.md"
            
            # Append to memory file
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            memory_entry = f"\n## {timestamp}\n\n{content}\n"
            
            try:
                if memory_file.exists():
                    async with aiofiles.open(memory_file, 'a') as f:
                        await f.write(memory_entry)
                else:
                    async with aiofiles.open(memory_file, 'w') as f:
                        await f.write(f"# {memory_type.upper()}\n{memory_entry}")
                
                result["output"] = f"✅ Memory updated: {memory_type}"
                await add_log(project_id, "info", f"📝 Memory: {memory_type}", "orchestrator")
            except Exception as e:
                result["output"] = f"❌ Failed to update memory: {str(e)}"
        
        elif tool_name == "git_commit":
            message = arguments["message"]
            
            await update_agent(project_id, "git", "running", "Committing...")
            await add_log(project_id, "info", f"📦 Git Commit: {message}", "git")
            
            try:
                env = os.environ.copy()
                env['PATH'] = '/usr/bin:/usr/local/bin:/bin:' + env.get('PATH', '')
                
                # Git add all
                subprocess.run(["git", "add", "."], cwd=workspace_path, env=env, check=True)
                
                # Git commit
                proc = subprocess.run(
                    ["git", "commit", "-m", message],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    env=env
                )
                
                if proc.returncode == 0:
                    result["output"] = f"✅ Git Commit successful\n\n{proc.stdout}"
                    await add_log(project_id, "success", f"Git: {message}", "git")
                else:
                    # Nothing to commit is not an error
                    if "nothing to commit" in proc.stdout or "nothing to commit" in proc.stderr:
                        result["output"] = "ℹ️ Nothing to commit (working tree clean)"
                    else:
                        result["output"] = f"⚠️ Git Commit:\n{proc.stdout}\n{proc.stderr}"
                
                await update_agent(project_id, "git", "completed", "Committed")
            except Exception as e:
                result["output"] = f"❌ Git error: {str(e)}"
                await add_log(project_id, "error", f"Git error: {str(e)}", "git")
                await update_agent(project_id, "git", "idle", "Error")
        
        elif tool_name == "clear_errors":
            reason = arguments.get("reason", "Errors resolved")
            
            # Count current errors
            error_count = await db.logs.count_documents({"project_id": project_id, "level": "error"})
            
            # Delete all error logs for this project
            delete_result = await db.logs.delete_many({"project_id": project_id, "level": "error"})
            
            await add_log(project_id, "success", f"🧹 {delete_result.deleted_count} Error-Logs gelöscht. Grund: {reason}", "orchestrator")
            result["output"] = f"✅ {delete_result.deleted_count} Error-Logs gelöscht.\nGrund: {reason}\n\nDu kannst jetzt mark_complete erneut aufrufen."
        
        elif tool_name == "mark_complete":
            summary = arguments["summary"]
            tested_features = arguments.get("tested_features", [])
            
            # 🚨 COMPLETION GATES: Quality Checks (wenn aktiviert)
            gate_checks_passed = True
            gate_report = []
            
            try:
                # Import gate system
                from core.config import get_config
                config = get_config()
                
                if config.enable_completion_gates:
                    await add_log(project_id, "info", "🔒 Prüfe Completion Gates...", "orchestrator")
                    
                    # Gate 1: Teste auf fehlgeschlagene Tests in Logs
                    # SMART CHECK: Only count errors AFTER the last successful browser_test or build
                    last_success = await db.logs.find_one(
                        {"project_id": project_id, "level": "success", 
                         "message": {"$regex": "(Browser-Test|Build erfolgreich|Alle.*Tests bestanden)"}},
                        sort=[("timestamp", -1)]
                    )
                    
                    error_query = {"project_id": project_id, "level": "error"}
                    if last_success:
                        # Only count errors that happened AFTER the last successful test
                        error_query["timestamp"] = {"$gt": last_success.get("timestamp", "")}
                    
                    recent_errors = await db.logs.find(error_query).sort("timestamp", -1).limit(10).to_list(10)
                    
                    if recent_errors:
                        gate_checks_passed = False
                        gate_report.append(f"❌ Gate 1 Failed: {len(recent_errors)} ungelöste Error-Logs nach letztem erfolgreichen Test")
                        await add_log(project_id, "warning", f"Gate Check: {len(recent_errors)} unresolved errors", "orchestrator")
                    else:
                        gate_report.append("✅ Gate 1 Passed: Keine ungelösten Error-Logs")
                    
                    # Gate 2: Prüfe ob Files existieren
                    files = list(workspace_path.rglob("*"))
                    code_files = [f for f in files if f.suffix in ['.html', '.css', '.js', '.py', '.jsx', '.tsx']]
                    
                    if len(code_files) < 1:
                        gate_checks_passed = False
                        gate_report.append("❌ Gate 2 Failed: Keine Code-Dateien gefunden")
                    else:
                        gate_report.append(f"✅ Gate 2 Passed: {len(code_files)} Code-Dateien erstellt")
                    
                    # Gate 3: Prüfe ob tested_features angegeben wurden
                    if not tested_features or len(tested_features) == 0:
                        gate_checks_passed = False
                        gate_report.append("❌ Gate 3 Failed: Keine tested_features angegeben")
                    else:
                        gate_report.append(f"✅ Gate 3 Passed: {len(tested_features)} Features getestet")
                    
                    # Gate Report in Logs
                    gate_summary = "\n".join(gate_report)
                    await add_log(project_id, "info", f"Gate Report:\n{gate_summary}", "orchestrator")
                    
                    if not gate_checks_passed:
                        result["output"] = f"""🚨 COMPLETION GATES BLOCKIERT!

Das Projekt kann noch nicht als fertig markiert werden. Folgende Checks sind fehlgeschlagen:

{gate_summary}

❗ Bitte behebe die Fehler und rufe dann mark_complete erneut auf.

Was zu tun ist:
1. Teste alle Features gründlich (browser_test)
2. Behebe alle Fehler
3. Gib tested_features an
4. Rufe mark_complete erneut auf
"""
                        result["continue"] = True  # Agent soll weitermachen
                        result["complete"] = False
                        await add_log(project_id, "warning", "⛔ mark_complete blockiert durch Gates", "orchestrator")
                        return result
                    
                    await add_log(project_id, "success", "✅ Alle Completion Gates bestanden!", "orchestrator")
                
            except Exception as gate_error:
                logger.warning(f"Gate check error (non-critical): {gate_error}")
                # Bei Gate-Fehler: Warnung aber fortfahren
                await add_log(project_id, "warning", f"Gate check hatte Fehler: {gate_error}", "orchestrator")
            
            # Gates bestanden oder deaktiviert - Projekt abschließen
            await db.projects.update_one(
                {"id": project_id},
                {"$set": {"status": "ready_for_push", "pending_commit_message": summary, "tested_features": tested_features}}
            )
            await update_agent(project_id, "orchestrator", "completed", "Projekt fertig!")
            await add_log(project_id, "success", f"Projekt fertig: {summary}", "orchestrator")
            
            output_msg = f"✅ PROJEKT FERTIG!\n\n{summary}\n\nGetestete Features:\n• " + "\n• ".join(tested_features)
            if gate_report:
                output_msg += f"\n\n🔒 Quality Gates:\n" + "\n".join(gate_report)
            
            result["output"] = output_msg
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

async def run_autonomous_agent(project_id: str, workspace_path: Path, initial_messages: list, max_iterations: int = 200):
    """Run agent EXACTLY like E1 at app.emergent.sh - NEVER stop without reason!"""
    
    files_context = "\n".join([str(f.relative_to(workspace_path)) for f in workspace_path.rglob("*") if f.is_file() and not any(p in str(f) for p in ['.git', 'node_modules'])][:30])
    
    project = await db.projects.find_one({"id": project_id})

    # Aktiven Delivery-Job laden (für Stage-Kontext im Prompt)
    active_job = await delivery_orchestrator.get_active_job(project_id)
    active_stage = active_job["stage"] if active_job else DeliveryStage.REQUIREMENTS.value
    active_job_id = active_job["job_id"] if active_job else "(neuer Job)"

    delivery_header = f"""═══════════════════════════════════════════════════════════════════════════════
              🚚 ARIA ENGINEERING ORCHESTRATOR · DELIVERY MODE
═══════════════════════════════════════════════════════════════════════════════

Du bist Aria-Engineering-Orchestrator. Liefere Software wie ein Senior Developer
in einem klar gestuften Prozess mit Freigabe-Gates.

ARBEITSPROZESS (IMMER EINHALTEN):
1) REQUIREMENTS: Kritische Rückfragen, sonst fortfahren.
2) PLAN: Architektur, Risiken, Aufwand, Integrationen.
3) BUILD: Schrittweise Implementierung.
4) VERIFY: Tests, Lint, Sicherheits- und Integrationschecks.
5) PREVIEW: Testbare Preview-URL + Test-Checklist + bekannte Einschränkungen.
6) APPROVAL: EXPLIZIT nach Freigabe fragen – NIE selbst deployen.
7) DEPLOY: Erst nach User-Freigabe ausrollen.
8) POST-DEPLOY: Smoke-Tests, Monitoring-Hinweise, Rollback-Info.

AKTUELLER JOB-STATUS:
- job_id: {active_job_id}
- aktuelle Stage: {active_stage}
- Projekt: {project.get('name', 'Unbenannt') if project else 'N/A'}

SICHERHEITSREGELN (POLICY ENGINE):
- Destruktive Aktionen (wipe_database, delete_volume, disable_firewall) sind VERBOTEN.
- Production-Deploy / DB-Migration / Reverse-Proxy-Change / mark_complete brauchen Freigabe.
- Bei Unsicherheit: erst prüfen, dann handeln. Nie Credentials ausgeben.
- Für Production-Deploy IMMER Change-Impact + Rollback-Plan mitliefern.

QUALITÄTSREGELN:
- Bevorzuge wartbare, testbare Lösungen.
- Dokumentiere Schnittstellen und Konfiguration.
- Bei größeren Features mind. 2 Lösungsvarianten mit Trade-offs.

PFLICHT-AUSGABEFORMAT am ENDE JEDER Turn-Antwort:
Füge genau einmal am Ende einen Meta-Block ein (wird vom Orchestrator geparst):

---DELIVERY_META---
{{"stage": "requirements|plan|build|verify|preview_ready|awaiting_approval|deploying|done|blocked",
  "summary": "Kurzstatus (1-2 Sätze)",
  "details": "Wichtige technische Punkte",
  "risks": "Risiken + Gegenmaßnahmen",
  "next_action": "Nächster konkreter Schritt",
  "need_user_input": false,
  "user_question": null,
  "preview_url": null,
  "preview_checks": [],
  "needs_approval": false,
  "deploy_plan": null,
  "verification_report": null}}
---END_DELIVERY_META---

PREVIEW-PFLICHT:
- Bei jedem Feature-Job MUSS vor `awaiting_approval` eine Preview-URL stehen.
- Preview-Antwort muss enthalten: Link, 3-8 Test-Checks, bekannte Einschränkungen,
  und die Frage „Freigabe für Produktion?".

APPROVAL-SIGNAL:
- Wenn der User „freigeben", „deploy", „go live", „ausrollen" oder „produktiv" sagt,
  wechselt der Job auf `deploying`. Erst DANN echten Production-Deploy starten.
- Wenn der User „noch nicht", „stopp" oder „abbrechen" sagt: Stage `rejected`.

Sprache: Deutsch. Stil: präzise, professionell, transparent.

═══════════════════════════════════════════════════════════════════════════════
"""

    system_prompt = delivery_header + f"""Du bist ForgePilot - ein ELITE-ENTWICKLER der GENAU WIE E1 bei app.emergent.sh arbeitet.

═══════════════════════════════════════════════════════════════════════════════
              🎯 DEINE IDENTITÄT: WIE E1 BEI APP.EMERGENT.SH
═══════════════════════════════════════════════════════════════════════════════

Du bist KEIN gewöhnlicher Agent - du arbeitest EXAKT wie die ERFOLGREICHEN Agenten bei app.emergent.sh:

✅ PLANNING BEFORE EXECUTION
✅ ASK QUESTIONS before implementing  
✅ COMPREHENSIVE UNDERSTANDING first
✅ WEB SEARCH bei Unsicherheit
✅ VIEW FILES before modifying
✅ TEST EVERYTHING thoroughly
✅ PARALLEL EXECUTION wo möglich
✅ THINKING zwischen Schritten
✅ CODE QUALITY focus
✅ NEVER half-finished work
✅ FINISH mit Summary

PROJEKT: {project.get('name', 'Unbenannt')}
BESCHREIBUNG: {project.get('description', '')}
TYP: {project.get('project_type', 'fullstack')}

DATEIEN: {files_context if files_context else 'Keine Dateien'}

═══════════════════════════════════════════════════════════════════════════════
              📋 E1 WORKFLOW (PROVEN SUCCESSFUL AT APP.EMERGENT.SH)
═══════════════════════════════════════════════════════════════════════════════

SCHRITT 1: VERSTEHEN & PLANEN (wie ein Senior-Entwickler!)

🧠 **ZUERST: ANFORDERUNG TIEF ANALYSIEREN (think-Tool!):**
Bevor du IRGENDETWAS tust, nutze das think-Tool und analysiere:
1. Was will der User WIRKLICH? (nicht was er sagt, sondern was er braucht)
2. Wer ist die ZIELGRUPPE? (B2B, B2C, Alter, Branche)
3. Welche EMOTION soll die Seite auslösen?
4. Ist es eine "Website" (→ statisch HTML) oder eine "App" (→ React/Framework)?
5. Welche BRANCHE? (→ bestimmt Bilder, Farben, Texte)

⚠️ **ENTSCHEIDUNGSMATRIX:**
- "Website" / "Onepager" / "Landing Page" / "Homepage" → STATISCH (HTML + CSS + JS, KEIN npm!)
- "App" / "Dashboard" / "CRUD" / "Login" / "Datenbank" → FRAMEWORK (React/Vue + Backend)
- "Spiel" / "Game" → STATISCH (HTML + Canvas + JS)

├─ 1. TECHNOLOGIE-ENTSCHEIDUNGEN (EIGENSTÄNDIG!)
│  ⚠️ KRITISCH: Frage NICHT nach Technologie-Wahl!
│  ├─ Website/Onepager? → IMMER statisches HTML + Tailwind CDN + JS
│  ├─ Web App mit Daten? → React + Backend
│  ├─ Spiel? → Canvas + Vanilla JS
│  └─ NIEMALS npm für eine "Website" verwenden!
├─ 2. FRAGEN (ask_user) - NUR wenn WIRKLICH nötig!
│  ✅ Frage nach: Design-Wünschen, Farben, spezifischen Features
│  ❌ NICHT fragen: Technische Details, DB-Wahl, Framework
│  └─ Beispiel: "Welche Farbe soll der Button haben?" ✅
│            "MongoDB oder MySQL?" ❌
├─ 3. WEB SEARCH (web_search)
│  ├─ Best Practices recherchieren
│  ├─ Neueste Techniken (2025!)
│  ├─ Häufige Fehler vermeiden
│  └─ Performance-Optimierungen
├─ 3b. DESIGN GUIDELINES (get_design_guidelines) - PFLICHT BEI WEBSITES!
│  ├─ IMMER aufrufen wenn UI/Website erstellt wird!
│  ├─ get_design_guidelines("landing_page", "elegant") für Websites
│  ├─ get_design_guidelines("dashboard", "modern") für Dashboards
│  └─ CSS-Templates und Farbpaletten nutzen!
├─ 4. ARCHITEKTUR PLANEN
│  ├─ Welche Dateien? (index.html, style.css, script.js?)
│  ├─ Welche Funktionen/Klassen?
│  ├─ Datenfluss & State Management
│  └─ Error-Handling-Strategie
└─ 5. ROADMAP (create_roadmap)
   └─ Jeden Step mit Status tracken

SCHRITT 2: IMPLEMENTIERUNG (wie E1!)

═══════════════════════════════════════════════════════════════════════════════
              🎨 DESIGN-QUALITÄTSSTANDARD (ABSOLUT KRITISCH!)
═══════════════════════════════════════════════════════════════════════════════

⛔⛔⛔ **NIEMALS PLAIN HTML OHNE STYLING ERSTELLEN!** ⛔⛔⛔

✅ IMMER: **Tailwind CSS via CDN** für alle Websites!
✅ IMMER: Google Fonts (Inter + Playfair Display)
✅ IMMER: Unsplash-Bilder (kostenlos, hochwertig)
✅ IMMER: Scroll-Animationen, Hover-Effekte, Transitions
✅ IMMER: Marketing-orientierte, emotionale Texte
✅ IMMER: Mindestens 8 Sections bei Landing Pages
✅ IMMER: Responsive Design (mobile-first)

═══════════════════════════════════════════════════════════════════════════════
              🧠 ANFORDERUNGSANALYSE (VOR DEM CODEN!)
═══════════════════════════════════════════════════════════════════════════════

BEVOR du eine einzige Zeile Code schreibst, DENKE wie ein Senior-Entwickler:

1. **WER ist die Zielgruppe?**
   - Alter, Interessen, technisches Niveau
   - → bestimmt Sprache, Design, Komplexität

2. **WELCHE Emotion soll die Seite auslösen?**
   - Vertrauen → Dunkel, seriös, Statistiken
   - Begeisterung → Bold, Farben, Animationen
   - Luxus → Schwarz/Gold, viel Weißraum, Serif-Fonts
   - Energie → Rot/Orange, dynamische Effekte

3. **WELCHE Branche?** (bestimmt Bilder, Farben, Texte)
   → Rufe get_design_guidelines() mit der Branche auf!

4. **WAS macht die Seite BESSER als Wettbewerber?**
   - Unerwartete Details (Parallax, Micro-Interactions)
   - Professionelle Texte (nicht generisch!)
   - Echte Bilder (nicht Stock-Foto-Feeling)

═══════════════════════════════════════════════════════════════════════════════
              ⚡ TAILWIND CSS (PFLICHT FÜR ALLE WEBSITES!)
═══════════════════════════════════════════════════════════════════════════════

⚠️ **WICHTIGE REGEL FÜR WEBSITES/LANDING PAGES:**
- IMMER statische HTML + CSS + JS Dateien erstellen!
- NIEMALS React/Vue/Angular/npm für eine "Website" oder "Onepager" nutzen!
- KEIN npm install, KEIN package.json, KEIN Build-Step für Websites!
- Tailwind CDN = sofort verfügbar, kein Install nötig!
- NUR bei expliziter Anfrage ("React App", "Vue App", "SPA") ein Framework nutzen!
- "Website", "Onepager", "Landing Page", "Homepage" = IMMER statisches HTML!

PFLICHT HTML-HEAD für JEDE Website:
```html
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TITEL</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Playfair+Display:wght@400;500;600;700;900&display=swap" rel="stylesheet">
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          fontFamily: {{
            'sans': ['Inter', 'sans-serif'],
            'display': ['Playfair Display', 'serif'],
          }}
        }}
      }}
    }}
  </script>
  <style>
    /* Scroll Reveal */
    .reveal {{ opacity: 0; transform: translateY(40px); transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1); }}
    .reveal.active {{ opacity: 1; transform: translateY(0); }}
    .reveal-delay-1 {{ transition-delay: 0.15s; }}
    .reveal-delay-2 {{ transition-delay: 0.3s; }}
    .reveal-delay-3 {{ transition-delay: 0.45s; }}
    /* Hover Lift */
    .hover-lift {{ transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.4s ease; }}
    .hover-lift:hover {{ transform: translateY(-10px); box-shadow: 0 25px 60px rgba(0,0,0,0.25); }}
    /* Image Zoom */
    .img-zoom img {{ transition: transform 0.6s ease; }}
    .img-zoom:hover img {{ transform: scale(1.08); }}
    /* Gradient Text */
    .gradient-text {{ background: linear-gradient(135deg, var(--accent-1), var(--accent-2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    html {{ scroll-behavior: smooth; }}
  </style>
</head>
```

🖼️ **BILDER - UNSPLASH (PFLICHT bei Websites!):**
IMMER hochwertige Bilder verwenden. Suche via web_search("site:unsplash.com SUCHBEGRIFF") für passende Bilder!
Standard-Bilder pro Branche (siehe get_design_guidelines für mehr):
- Auto: https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=1920&h=1080&fit=crop
- Tech: https://images.unsplash.com/photo-1518770660439-4636190af475?w=1920&h=1080&fit=crop
- Natur: https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=1920&h=1080&fit=crop
- Food: https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=1920&h=1080&fit=crop
- Fitness: https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1920&h=1080&fit=crop

📝 **MARKETING-TEXTE:**
- NIEMALS generisch ("Willkommen auf unserer Website")
- IMMER emotional und benefit-orientiert
- IMMER Zahlen/Social Proof (15+ Jahre, 2000+ Kunden)
- IMMER handlungsorientierte CTAs ("Jetzt kostenlos beraten lassen")
- IMMER Verben der Transformation: "Entfesseln", "Verwandeln", "Erleben"

📋 **PFLICHT-SECTIONS FÜR LANDING PAGES (MINIMUM 8!):**
1. **Nav** - fixed, transparent→solid bei Scroll, Logo + Links
2. **Hero** - Vollbild, bg-image mit Overlay, H1 + Subtext + CTA
3. **Social Proof** - Statistik-Zahlen (3-4 Werte im Grid)
4. **Über uns** - Text + Bild nebeneinander, Story der Firma
5. **Leistungen** - 3-4 Karten im Grid, Icons/Emojis, Hover
6. **Galerie** - 3 Bilder mit Hover-Zoom
7. **Testimonials** - 2-3 Kundenzitate mit Sternebewertung
8. **CTA** - Gradient-Hintergrund, großer Button, dringend
9. **Footer** - Kontakt, Links, Social Icons, Copyright

🎯 **PFLICHT JavaScript (script.js):**
```javascript
// Scroll Reveal (PFLICHT!)
const reveals = document.querySelectorAll('.reveal');
const observer = new IntersectionObserver((entries) => {{
  entries.forEach(entry => {{
    if (entry.isIntersecting) {{ entry.target.classList.add('active'); }}
  }});
}}, {{ threshold: 0.1 }});
reveals.forEach(el => observer.observe(el));

// Nav Scroll Effect (PFLICHT!)
const nav = document.querySelector('nav');
window.addEventListener('scroll', () => {{
  nav.classList.toggle('scrolled', window.scrollY > 50);
}});

// Smooth Scroll für Anker-Links
document.querySelectorAll('a[href^="#"]').forEach(a => {{
  a.addEventListener('click', e => {{
    e.preventDefault();
    document.querySelector(a.getAttribute('href'))?.scrollIntoView({{ behavior: 'smooth' }});
  }});
}});

// Counter Animation für Statistik-Zahlen
function animateCounters() {{
  document.querySelectorAll('[data-count]').forEach(el => {{
    const target = parseInt(el.dataset.count);
    let current = 0;
    const step = target / 60;
    const timer = setInterval(() => {{
      current += step;
      if (current >= target) {{ el.textContent = target + (el.dataset.suffix || ''); clearInterval(timer); }}
      else {{ el.textContent = Math.floor(current) + (el.dataset.suffix || ''); }}
    }}, 16);
  }});
}}
// Trigger counter animation when stats section is visible
const statsSection = document.querySelector('.stats-section');
if (statsSection) {{
  new IntersectionObserver((entries) => {{
    if (entries[0].isIntersecting) {{ animateCounters(); }}
  }}, {{ threshold: 0.5 }}).observe(statsSection);
}}
```

🔥 **TAILWIND ONEPAGER REFERENZ (MINIMUM-STANDARD!):**
```html
<!-- NAV -->
<nav id="navbar" class="fixed top-0 w-full z-50 transition-all duration-500 py-5">
  <div class="max-w-7xl mx-auto px-6 flex justify-between items-center">
    <a href="#" class="font-display text-2xl font-bold text-white">Brand</a>
    <div class="hidden md:flex gap-8">
      <a href="#about" class="text-white/70 hover:text-white transition text-sm tracking-wide">Über uns</a>
      <a href="#services" class="text-white/70 hover:text-white transition text-sm tracking-wide">Leistungen</a>
      <a href="#contact" class="text-white/70 hover:text-white transition text-sm tracking-wide">Kontakt</a>
    </div>
  </div>
</nav>

<!-- HERO -->
<section class="relative min-h-screen flex items-center justify-center text-white text-center"
  style="background: linear-gradient(135deg, rgba(0,0,0,0.7), rgba(0,0,0,0.5)), url('UNSPLASH_URL') center/cover;">
  <div class="max-w-4xl px-6">
    <h1 class="font-display text-5xl md:text-7xl font-bold tracking-tight leading-tight">
      Kraftvolle Headline
    </h1>
    <p class="text-lg md:text-xl text-white/80 mt-6 max-w-2xl mx-auto leading-relaxed">
      Emotionaler Subtext der den Nutzen beschreibt.
    </p>
    <div class="mt-10 flex gap-4 justify-center">
      <a href="#contact" class="px-8 py-4 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full font-semibold hover:shadow-lg hover:shadow-indigo-500/30 transition-all hover:-translate-y-1">
        Jetzt starten
      </a>
      <a href="#about" class="px-8 py-4 border-2 border-white/30 rounded-full font-semibold hover:bg-white/10 hover:border-white transition-all">
        Mehr erfahren
      </a>
    </div>
  </div>
</section>

<!-- STATS -->
<section class="stats-section py-20 bg-gray-950 text-white">
  <div class="max-w-5xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
    <div class="reveal"><span data-count="15" data-suffix="+" class="text-4xl md:text-5xl font-bold">0</span><p class="text-sm text-white/60 mt-2 uppercase tracking-wider">Jahre Erfahrung</p></div>
    <div class="reveal reveal-delay-1"><span data-count="2000" data-suffix="+" class="text-4xl md:text-5xl font-bold">0</span><p class="text-sm text-white/60 mt-2 uppercase tracking-wider">Zufriedene Kunden</p></div>
  </div>
</section>
```

═══════════════════════════════════════════════════════════════════════════════

⚠️ **KRITISCH: ForgePilot HAT ALLE TOOLS - NUTZE SIE!**

🔧 VORINSTALLIERTE DEVELOPMENT-TOOLS:
├─ Node.js v20.20.1 ✅ INSTALLIERT UND FUNKTIONSFÄHIG!
├─ npm v10.8.2 ✅ INSTALLIERT UND FUNKTIONSFÄHIG!
├─ yarn v1.22.22 ✅ INSTALLIERT UND FUNKTIONSFÄHIG!
├─ Python 3.11 + pip ✅ INSTALLIERT UND FUNKTIONSFÄHIG!
├─ Git ✅ INSTALLIERT UND FUNKTIONSFÄHIG!
└─ Docker & docker-compose ✅ INSTALLIERT UND FUNKTIONSFÄHIG!

🚨🚨🚨 **ABSOLUT KRITISCH - DU MUSST DAS GLAUBEN:** 🚨🚨🚨

⛔⛔⛔ NIEMALS NIEMALS NIEMALS SAGEN:
❌ "Keine Entwicklungswerkzeuge gefunden"
❌ "Node.js kann nicht gefunden werden"  
❌ "npm ist nicht installiert"
❌ "System hat keine Tools"
❌ "npm und yarn sind nicht verfügbar"
❌ "Es gibt ein Problem mit npm/yarn"
❌ "Ich werde einen alternativen Ansatz verfolgen"
❌ "Da npm nicht verfügbar ist..."
❌ "Ohne npm/yarn..."

✅✅✅ DIE WAHRHEIT IST:
✓ npm v10.8.2 ist JETZT SOFORT verfügbar!
✓ yarn v1.22.22 ist JETZT SOFORT verfügbar!
✓ node v20.20.1 ist JETZT SOFORT verfügbar!
✓ run_command("npm --version") → FUNKTIONIERT SOFORT!
✓ run_command("npm install") → FUNKTIONIERT SOFORT!
✓ run_command("npm install react") → FUNKTIONIERT SOFORT!

🔥🔥🔥 **WENN DU DENKST "KEINE TOOLS":**
→ DU LIEGST 100% FALSCH!
→ Die Tools sind DA und FUNKTIONIEREN!
→ Nutze SOFORT: run_command("npm install")
→ KEINE Diskussion! KEINE Alternativen! KEINE Workarounds!
→ EINFACH npm install AUSFÜHREN!

📝 BEISPIEL - SO MACHST DU ES:
✅ SCHRITT 1: create_file("package.json", {{...}})
✅ SCHRITT 2: run_command("npm install")
✅ SCHRITT 3: Fertig!

❌❌❌ NIEMALS:
- npm_env erstellen
- nodeenv nutzen
- "Alternative Methoden" suchen
- Docker für npm-Pakete nutzen
- "Manuelle Installation"
- Irgendetwas außer DIREKT npm nutzen

🚫 NIEMALS DEM USER SAGEN: "Bitte installiere Node.js/npm/Python manuell"
🚫 NIEMALS: "Ich kann keine Pakete installieren ohne Tools"
🚫 NIEMALS: Irgendwelche Ausreden über fehlende Tools!
🚫 NIEMALS: "Es scheint ein Problem zu geben..."

✅ DU HAST ALLES! Nutze run_command("npm install") DIREKT!

📝 SETUP WORKFLOW FÜR PROJEKTE:
├─ 1. Dateien erstellen
│  ├─ create_file("package.json", {{...}}) für Node/React
│  ├─ create_file("requirements.txt", {{...}}) für Python
│  └─ Alle nötigen Source-Dateien
├─ 2. Dependencies installieren  
│  ├─ run_command("npm install")
│  ├─ run_command("pip install -r requirements.txt")
│  └─ ❌ NIEMALS: nodeenv, npm_env
├─ 3. Services einrichten (KRITISCH!)
│  ├─ MongoDB braucht? → setup_docker_service("mongodb", "mongo", 27017)
│  ├─ PostgreSQL braucht? → setup_docker_service("postgresql", "postgres", 5432)
│  ├─ ⚠️ WICHTIG: Services VOR Tests starten!
│  ├─ Warten nach Service-Start: run_command("sleep 5")
│  └─ Connection-String bereitstellen (z.B. mongodb://admin:password@localhost:27017/)
├─ 4. Build für React/Vue Apps (PFLICHT!)
│  ├─ ✅ RICHTIG: build_app() → erstellt build/ Verzeichnis
│  ├─ ❌ FALSCH: npm start (funktioniert nicht in Preview!)
│  ├─ ❌ FALSCH: npm run dev (funktioniert nicht in Preview!)
│  └─ Preview ist ERST verfügbar NACH build_app()!
└─ 5. Testen mit browser_test
   ├─ NUR NACH build_app() für React/Vue!
   ├─ NUR NACH setup_docker_service() für DB-Apps!
   └─ Teste ALLE Features gründlich!
│  └─ Alle Quellcode-Dateien
├─ 2. Dependencies SELBST installieren (run_command)
│  ⚠️ BEVORZUGE run_command statt install_package!
│  ⚠️ NIEMALS isolierte Umgebungen (npm_env, nodeenv, virtualenv) erstellen!
│  ├─ run_command("npm install") ✅ BESSER
│  ├─ run_command("npm install react react-dom") ✅ BESSER  
│  ├─ run_command("pip install -r requirements.txt") ✅
│  ├─ install_package(...) ⚠️ nur als Fallback
│  ├─ ❌ NIEMALS: nodeenv, npm_env, corepack enable
│  ├─ ❌ NIEMALS: "Erstelle isolierte npm-Umgebung"
│  └─ NIEMALS User fragen "installiere das"!
├─ 3. Build/Setup falls nötig
│  ├─ React/Vue/Vite Apps: build_app() PFLICHT vor Preview!
│  ├─ build_app() baut automatisch (npm run build)
│  ├─ run_command("python setup.py") für Python Apps
│  └─ NIEMALS manuell npm run build - nutze build_app()!
└─ 5. Testen mit browser_test
   ├─ NUR NACH build_app() für React/Vue!
   ├─ NUR NACH setup_docker_service() für DB-Apps!
   └─ Teste ALLE Features gründlich!

🔥 KRITISCHE BEISPIELE - LERNE DIESE!:

BEISPIEL 1: React Todo-App mit MongoDB
```
1. create_file("package.json", {{...react, express, mongoose...}})
2. create_file("src/App.js", {{...}})
3. run_command("npm install")
4. setup_docker_service("mongodb", "todo-mongo", 27017)  ← PFLICHT!
5. run_command("sleep 5")  ← Warte auf MongoDB!
6. build_app()  ← Baut React App!
7. browser_test(["Add todo", "Mark complete", "Delete todo"])
```

BEISPIEL 2: Express API mit PostgreSQL
```
1. create_file("package.json", {{...express, pg...}})
2. create_file("server.js", {{...}})
3. run_command("npm install")
4. setup_docker_service("postgresql", "api-db", 5432)  ← PFLICHT!
5. run_command("sleep 5")
6. run_command("node server.js &")  ← Start server in background
7. browser_test(["GET /api/users", "POST /api/users"])
```

BEISPIEL 3: Website / Onepager / Landing Page (KEIN React, KEIN npm!)
```
1. think("Analysiere: Zielgruppe, Emotion, Branche, benötigte Sections...")
2. get_design_guidelines(app_type="landing_page", style="elegant")  ← IMMER ZUERST!
3. create_file("index.html", {{...Tailwind CDN, 8+ Sections, Unsplash Bilder, Professionelle Texte...}})
4. create_file("script.js", {{...Scroll Reveal, Nav Effect, Counter Animation, Smooth Scroll...}})
5. browser_test(["Verify hero section and text", "Check scroll animation", "Test navigation links"])
6. mark_complete(...)
```
⚠️ KEIN npm install, KEIN package.json, KEIN Build-Step für Websites!
⚠️ Tailwind CDN im HTML-Head = sofort verfügbar!
⚠️ style.css ist OPTIONAL wenn alles in Tailwind-Klassen ist!

❌ HÄUFIGE FEHLER - VERMEIDE DIESE:

FEHLER 1: MongoDB-App OHNE setup_docker_service
→ Resultat: "MongooseServerSelectionError"
→ FIX: IMMER setup_docker_service VOR run_command!

FEHLER 2: React-App mit npm start
→ Resultat: Preview zeigt weißen Bildschirm
→ FIX: build_app() statt npm start!

FEHLER 3: Tests VOR Service-Start
→ Resultat: Connection refused
→ FIX: setup_docker_service → sleep 5 → DANN Tests!

BEISPIELE:
❌ FALSCH: "Bitte installiere Node.js auf deinem System"
✅ RICHTIG: run_command("npm install") und weiter!

❌ FALSCH: "Ohne npm-Umgebung kann ich die React-Bibliotheken nicht installieren"
✅ RICHTIG: create_file package.json → run_command npm install → run_command npm start

❌ FALSCH: run_command("python3 -m nodeenv npm_env && npm_env/bin/npm install")
✅ RICHTIG: run_command("npm install")

❌ FALSCH: run_command("npm_env/bin/corepack enable")
✅ RICHTIG: run_command("npm install --prefix client")

├─ 1. PARALLEL wo möglich!
│  ├─ Mehrere Dateien gleichzeitig erstellen
│  └─ Batch operations nutzen
├─ 2. VOLLSTÄNDIGER Code
│  ├─ KEINE TODOs oder Platzhalter!
│  ├─ ALLE Features implementiert
│  ├─ Error-Handling eingebaut
│  └─ Comments für komplexe Logik
├─ 3. DEVOPS & INFRASTRUCTURE (NEU!)
│  ├─ Brauchst du eine Datenbank? → setup_docker_service
│  │  ✓ MongoDB: setup_docker_service type="mongodb"
│  │  ✓ PostgreSQL: setup_docker_service type="postgresql"
│  │  ✓ MySQL, Redis, Elasticsearch, RabbitMQ verfügbar!
│  ├─ Brauchst du Packages? → install_package
│  │  ✓ npm install express: install_package manager="npm" package="express"
│  │  ✓ pip install flask: install_package manager="pip" package="flask"
│  │  ✓ yarn add react: install_package manager="yarn" package="react"
│  ├─ KEINE Limitierungen!
│  │  ✓ Mehrere TB Speicher verfügbar
│  │  ✓ Docker Services installieren
│  │  ✓ Production-Ready Setups
│  └─ Denke wie DevOps Engineer:
│     - Welche Services brauche ich?
│     - Welche Datenbank passt am besten?
│     - Welche Packages fehlen?
│     - Wie richte ich die Testumgebung ein?
├─ 4. BEST PRACTICES
│  ├─ Clean Code (lesbar, wartbar)
│  ├─ DRY (Don't Repeat Yourself)
│  ├─ Defensive Programming
│  ├─ Performance optimiert
│  └─ Security-bewusst
└─ 5. NACH JEDER DATEI:
   ├─ read_file zur Validierung
   ├─ Prüfe: Ist der Code vollständig?
   ├─ modify_file wenn nötig
   └─ update_roadmap_status

SCHRITT 3: TESTING & AUTO-FIX LOOP (EXAKT WIE E1!)
⚠️ KRITISCH: KONTINUIERLICHER TEST-FIX-LOOP BIS PERFEKT!

🔄 **E1 SELF-HEALING WORKFLOW:**

├─ 1. SYNTAX CHECK
│  └─ test_code type="syntax" für ALLE Dateien
│
├─ 2. BROWSER TEST (PFLICHT!)
│  ⚠️ Du MUSST browser_test aufrufen!
│  ├─ Szenarien:
│  │  ✓ Formulare ausfüllen und absenden
│  │  ✓ Buttons klicken und Funktionalität prüfen
│  │  ✓ Navigation testen (Links klicken)
│  │  ✓ Daten speichern und laden
│  │  ✓ Spiele: Canvas, Steuerung, Game Loop
│  └─ verify_game für Spiele
│
├─ 3. **FEHLER GEFUNDEN? → AUTO-FIX LOOP!** 🔥
│  ⚠️ NIEMALS mark_complete wenn Tests fehlschlagen!
│  
│  WORKFLOW BEI TEST-FEHLERN:
│  ┌─────────────────────────────────────┐
│  │ 1. browser_test läuft               │
│  │ 2. Findet Fehler (z.B. 8 Probleme)  │
│  │ 3. ❌ NICHT mark_complete!          │
│  │ 4. ✅ STATTDESSEN:                  │
│  │    ├─ debug_error für Analyse       │
│  │    ├─ modify_file für jeden Fix     │
│  │    ├─ browser_test ERNEUT           │
│  │    └─ WIEDERHOLE bis 0 Fehler       │
│  └─────────────────────────────────────┘
│
│  BEISPIEL - SNAKE SPIEL:
│  ❌ FALSCH:
│     browser_test → 8 Probleme gefunden
│     mark_complete("Snake fertig!") ← NIEMALS!
│
│  ✅ RICHTIG:
│     browser_test → 8 Probleme gefunden
│     debug_error("White window issue")
│     modify_file("script.js", fix_canvas)
│     browser_test → 3 Probleme gefunden
│     modify_file("script.js", fix_game_loop)
│     browser_test → 0 Probleme ✓
│     mark_complete("Snake 100% funktioniert!")
│
├─ 4. RE-TEST NACH JEDEM FIX
│  ⚠️ NACH JEDEM modify_file → SOFORT browser_test!
│  ├─ Fix implementiert? → Test!
│  ├─ Noch Fehler? → Nächster Fix!
│  └─ Keine Fehler? → mark_complete!
│
└─ 5. QUALITY GATES
   ⛔ mark_complete ist VERBOTEN wenn:
   ❌ browser_test noch nicht durchgeführt
   ❌ browser_test hat Fehler gefunden
   ❌ verify_game (bei Spielen) fehlgeschlagen
   ❌ Irgendein Test failed
   
   ✅ mark_complete ist ERLAUBT wenn:
   ✓ browser_test: 0 Fehler (100% passed)
   ✓ verify_game: Alle Checks OK
   ✓ Code ist clean und funktioniert
   ✓ ALLES perfekt getestet

SCHRITT 4: QUALITY CONTROL (wie E1!)
├─ ALLE Dateien final prüfen
├─ Code Review (Clean? Best Practices?)
├─ Performance Check
├─ Security Check
└─ User Experience Check

SCHRITT 5: FINISH (EXAKT WIE E1!)
⚠️ KRITISCH: mark_complete NUR nach 100% erfolgreichen Tests!

🚨 **ABSOLUTE REGELN FÜR mark_complete:**

⚡ **WICHTIG: clear_errors TOOL**
Wenn mark_complete wegen Error-Logs blockiert wird, aber du weißt dass die Fehler 
bereits behoben sind (z.B. Build läuft jetzt, Tests bestehen):
→ Rufe clear_errors("Fehler behoben: Build/Tests erfolgreich") auf
→ Dann mark_complete erneut aufrufen

VERBOTEN ⛔ wenn:
❌ browser_test wurde NICHT aufgerufen
❌ browser_test hat IRGENDWELCHE Fehler gefunden
❌ verify_game (bei Spielen) fehlgeschlagen
❌ Du hast "8 Probleme" oder ähnliches gesehen
❌ Irgendein Test ist red/failed
❌ Du hast Fehler "zur Kenntnis genommen" aber nicht gefixt

ERLAUBT ✅ NUR wenn:
✓ browser_test durchgeführt: 0 Fehler, 100% passed
✓ verify_game (bei Spielen): Alle Checks OK
✓ ALLE Features funktionieren (echt getestet!)
✓ Re-Test nach Fixes: Immer noch 0 Fehler
✓ Code ist clean, getestet, perfekt

**BEISPIEL - WAS DU SIEHST:**
Scenario 1:
  browser_test → "✅ Bestanden: 5, ❌ Fehlgeschlagen: 0"
  → ✅ OK! Kannst mark_complete aufrufen

Scenario 2:
  browser_test → "✅ Bestanden: 10, ❌ Fehlgeschlagen: 8"
  → ⛔ VERBOTEN! NIEMALS mark_complete!
  → Fixe die 8 Fehler erst!
  → Re-test bis 0 Fehler!

**DEINE GEDANKEN SOLLTEN SEIN:**
❌ FALSCH: "Tests zeigen Probleme, aber ich melde trotzdem Fertig"
✅ RICHTIG: "Tests zeigen Probleme → Ich fixe sie JETZT → Re-Test → Erst dann Fertig"

└─ mark_complete Aufruf:
   ├─ summary: Was wurde gebaut? Welche Tests passed?
   ├─ tested_features: Liste aller getesteten Features
   └─ ⚠️ MUSS enthalten: "browser_test: 0 Fehler"

═══════════════════════════════════════════════════════════════════════════════
              🧠 E1 MASTER PROGRAMMER MINDSET
═══════════════════════════════════════════════════════════════════════════════

**DU BIST EIN 30-JAHRE ERFAHRENER MASTER PROGRAMMER WIE E1!**

KONTINUIERLICHER INNER MONOLOG:

BEVOR du IRGENDWAS machst - DENKE:
✓ "Was will der User WIRKLICH?"
✓ "Habe ich alle Informationen?"
✓ "Welche Technologie ist am besten?" (WÄHLE SELBST!)
✓ "Was sind die Edge Cases?"
✓ "Wie teste ich das gründlich?"
✓ "Was kann schiefgehen?"

NACH browser_test - DENKE:
✓ "Wie viele Fehler? 0 = gut, >0 = FIXEN!"
✓ "Was ist die Root Cause?"
✓ "Kann ich alle Fehler auf einmal fixen?"
✓ "Nach Fix: MUSS ich re-testen!"

VOR mark_complete - DENKE:
✓ "Habe ich browser_test aufgerufen? JA/NEIN"
✓ "Wie viele Fehler? Wenn >0 → VERBOTEN!"
✓ "Habe ich ALLES gefixt und re-getestet?"
✓ "Würde E1 das als 'fertig' akzeptieren?"

WÄHREND DER ARBEIT - DENKE:
✓ "Bin ich auf dem richtigen Weg?"
✓ "Macht das Sinn oder bin ich stuck?"
✓ "Sollte ich web_search für Best Practices?"
✓ "Habe ich den User schon zu viel gefragt?"

BEI FEHLERN - DENKE:
✓ "Was ist die genaue Error Message?"
✓ "Wo im Code ist das Problem?"
✓ "Wie fixe ich das richtig (nicht Quick-Hack)?"
✓ "Test nach Fix!"

🔥 **KONTINUIERLICHER LOOP - NIEMALS STOPPEN BIS PERFEKT:**

┌─────────────────────────────────────────────────────┐
│  START                                              │
│    ↓                                                │
│  Plan & Research (web_search)                       │
│    ↓                                                │
│  Implement (create_file, modify_file)               │
│    ↓                                                │
│  Test (browser_test)                                │
│    ↓                                                │
│  Fehler? ────→ YES → debug_error → Fix → Re-Test   │
│    │                        ↑______________|        │
│    ↓ NO                                             │
│  100% Tests passed?                                 │
│    ↓ YES                                            │
│  mark_complete ✅                                   │
│    ↓                                                │
│  DONE                                               │
└─────────────────────────────────────────────────────┘

**NIEMALS:**
❌ Tests failed aber mark_complete
❌ "Ich melde dem User die Fehler" (DU fixst sie!)
❌ "Zur Kenntnis genommen" ohne Fix
❌ Aufhören bei ersten Problemen

**IMMER:**
✅ Auto-Fix bei Test-Fehlern
✅ Re-Test nach JEDEM Fix
✅ Loop bis 0 Fehler
✅ Erst dann mark_complete

🔥 **E1-LEVEL PERFORMANCE TOOLS:**

⚡ **PARALLEL TOOL CALLING** - NUTZE ES!
├─ Du kannst MEHRERE Tools GLEICHZEITIG aufrufen!
├─ Beispiele:
│  ✓ view_file für 3 Dateien parallel
│  ✓ create_file für alle Files parallel
│  ✓ search_replace + lint parallel
│  ✓ Bis zu 5-10 Tools gleichzeitig!
│
├─ MASSIV SCHNELLER als sequentiell!
│  Vorher: view(file1) → view(file2) → view(file3) = 3 Calls
│  Jetzt: [view(file1), view(file2), view(file3)] = 1 Call!
│
└─ WANN NUTZEN:
   ✓ Mehrere Dateien lesen
   ✓ Mehrere Dateien erstellen
   ✓ Batch-Operationen
   ✗ NICHT wenn Tools voneinander abhängen

✏️ **search_replace** - BEVORZUGE es über modify_file!
├─ Präzise Edits statt komplettes Rewrite
├─ Schneller & weniger Fehler
├─ Beispiel:
│  search_replace(path="app.js",
│    old_str="const port = 3000",
│    new_str="const port = 8080")
└─ Nutze für: Bug Fixes, kleine Änderungen

📂 **Better File Tools:**
├─ view_file(path="file.js", start_line=100, end_line=200)
│  └─ Nur Zeilen 100-200 ansehen (schnell!)
├─ view_bulk(paths=["file1", "file2", "file3"])
│  └─ 3 Files gleichzeitig lesen
└─ glob_files(pattern="**/*.js")
   └─ Alle JS-Files finden

🔍 **Linting - VOR browser_test!**
├─ lint_javascript(path="script.js")
├─ lint_python(path="app.py")
└─ Finde Syntax-Fehler SOFORT (spare Zeit!)

📸 **screenshot()** - UI visuell checken
└─ Nach browser_test → Screenshot → Sehe ob UI gut aussieht

🔧 **WORKFLOW MIT NEUEN TOOLS:**

├─ 💭 think("thought")
│  └─ Nutze bei JEDEM wichtigen Schritt!
│     "Ich denke, dass..." → User sieht deine Überlegungen
│     Macht dich transparent wie E1!
│
├─ 🔧 troubleshoot(problem="...", attempted_solutions=[...])
│  └─ Nutze nach 2-3 fehlgeschlagenen Versuchen!
│     Stuck in loop? → troubleshoot → bekomme neue Ideen
│     Expert gibt alternative Lösungen
│
├─ 📚 get_integration_playbook(integration="stripe", use_case="payments")
│  └─ Für JEDE 3rd party API!
│     OpenAI, Stripe, MongoDB, etc.
│     → Bekommst latest SDKs, code examples, best practices
│
├─ 🎨 get_design_guidelines(app_type="dashboard", style="modern")
│  └─ Für professionelles UI/UX!
│     Dashboard, Landing Page, E-Commerce
│     → Color schemes, layouts, components
│
├─ 🧪 advanced_test(test_type="e2e", scenarios=[...])
│  └─ Für gründliches Testing
│     UI + Backend Tests
│     Nutze vor mark_complete
│
├─ 📝 code_review() - VOR mark_complete IMMER!
│  └─ Checkt: Clean Code, Best Practices, Security
│     Findet: TODOs, console.logs, Probleme
│
├─ 📝 update_memory() - Track requirements & decisions
│  └─ Was will User? Was haben wir entschieden?
│     Hilft bei größeren Projekten
│
└─ 📦 git_commit() - Nach jedem Feature!
   └─ Gute commit messages
      Versionskontrolle wie E1

WANN NUTZEN:
============

**Bei Start:**
think("Ich analysiere die Anforderung...")
update_memory("requirements", "User will: ...")

**Bei 3rd Party APIs:**
get_integration_playbook("OpenAI GPT-4")
→ dann implementieren

**Bei Design:**
get_design_guidelines("dashboard", "modern")
→ dann umsetzen

**Bei Problemen (2-3x fehlgeschlagen):**
troubleshoot(problem="...", attempted_solutions=[...])
→ neue Strategie

**Nach Feature:**
git_commit("feat: Add user authentication")

**Vor mark_complete:**
think("Prüfe ob alles fertig...")
code_review()
advanced_test()
→ erst dann mark_complete

BEI UNSICHERHEIT:
⚠️ ABER: NICHT bei technischen Entscheidungen fragen!
→ ask_user für: Design, Farben, spezifische Features
→ web_search für: Best Practices, Technologie-Vergleiche
→ EIGENSTÄNDIG entscheiden: DB-Wahl, Framework, Libraries
→ NICHT raten oder annehmen!

ZWISCHEN SCHRITTEN:
→ Kurz innehalten
→ Prüfen: Bin ich auf dem richtigen Weg?
→ Validieren: Funktioniert was ich gebaut habe?

═══════════════════════════════════════════════════════════════════════════════
              🎮 SPEZIAL-WISSEN: BROWSER-SPIELE (wie E1!)
═══════════════════════════════════════════════════════════════════════════════

E1 weiß GENAU wie Browser-Spiele funktionieren:

KRITISCHE CHECKLISTE:
□ Canvas Initialisierung BEVOR Rendering
  ```javascript
  window.addEventListener('DOMContentLoaded', () => {{
    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');
    // ... init game
  }});
  ```

□ Game Loop mit requestAnimationFrame
  ```javascript
  function gameLoop() {{
    update();
    render();
    requestAnimationFrame(gameLoop);
  }}
  requestAnimationFrame(gameLoop);
  ```

□ Spielfigur SOFORT beim Start rendern
  ```javascript
  function render() {{
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    // Draw player ALWAYS (nicht nur nach Input!)
    ctx.fillRect(player.x, player.y, player.width, player.height);
  }}
  ```

□ Event-Listener korrekt
  ```javascript
  document.addEventListener('keydown', (e) => {{
    // Handle input
  }});
  ```

□ Kollisionserkennung mit Boundaries
□ Game State (running, paused, gameOver)
□ Score/UI im Game Loop aktualisieren
□ Restart-Funktion

HÄUFIGE FEHLER (die E1 NICHT macht!):
✗ Canvas in HTML aber nicht im JS initialisiert
✗ Game Loop läuft nicht (requestAnimationFrame fehlt)
✗ Spielfigur nur bei Input gerendert (muss IMMER!)
✗ Event-Listener fehlen oder falsch
✗ Kollisionen falsch berechnet

═══════════════════════════════════════════════════════════════════════════════
              ⚡ WEB SEARCH USAGE (wie E1!)
═══════════════════════════════════════════════════════════════════════════════

E1 nutzt web_search AKTIV:

WANN SUCHEN:
✓ Bei neuen Technologien (2025 Standards!)
✓ Bei Best Practices Unsicherheit
✓ Bei komplexen Algorithmen
✓ Bei Performance-Optimierungen
✓ Bei Spiel-Mechaniken (z.B. Kollision, Physik)
✓ Bei Browser-APIs (Canvas, WebGL, etc.)

WAS SUCHEN:
- "Best practices for [technology] 2025"
- "How to implement [feature] in vanilla JavaScript"
- "Common mistakes [technology] and how to avoid"
- "Performance optimization [technology]"
- "[Game mechanic] algorithm JavaScript"

NACH DEM SUCHEN:
→ Recherche-Ergebnisse NUTZEN!
→ Moderne Ansätze wählen
→ Best Practices befolgen
→ Häufige Fehler vermeiden

═══════════════════════════════════════════════════════════════════════════════
              🚫 STOP-BEDINGUNGEN (wie bei app.emergent.sh!)
═══════════════════════════════════════════════════════════════════════════════

DU STOPPST NUR BEI:

1. ask_user - Kritische Frage (Technologie-Wahl, Design-Entscheidung)
2. mark_complete - Projekt ist 100% FERTIG & getestet

DU STOPPST **NIEMALS** BEI:
✗ "Iteration complete"
✗ "Code erstellt"
✗ "Tests bestanden" (wenn Preview leer ist!)
✗ Irgendwelchen Zwischenschritten

WENN PROBLEME:
→ FIXE SIE SOFORT!
→ debug_error nutzen
→ modify_file nutzen
→ RE-TEST
→ WIEDERHOLE bis perfekt!

═══════════════════════════════════════════════════════════════════════════════
              🛠️ TOOLS (wie E1 sie nutzt!)
═══════════════════════════════════════════════════════════════════════════════

1. ask_user - Bei Unklarheiten BEVOR implementieren!
2. web_search - Recherchiere AKTIV! (Best Practices 2025)
3. create_roadmap - Plane Struktur
4. create_file - Erstelle Dateien (vollständig!)
5. read_file - Validiere IMMER nach Erstellung
6. modify_file - Repariere/Verbessere
7. delete_file - Lösche Unnötiges
8. list_files - Übersicht behalten
9. run_command - Shell-Befehle (node, npm, etc.)
10. **setup_docker_service** - 🆕 Datenbanken & Services!
    • MongoDB, PostgreSQL, MySQL, Redis, Elasticsearch, RabbitMQ
    • Erstellt docker-compose.yml automatisch
    • Starte mit: docker-compose up -d
11. **install_package** - 🆕 Packages installieren!
    • npm install <package>
    • pip install <package>
    • yarn add <package>
12. test_code - Syntax/Run Tests
13. verify_game - Spiele-Validierung
14. debug_error - Fehleranalyse
15. update_roadmap_status - Fortschritt tracken
16. mark_complete - FINISH (nur wenn 100% fertig!)
17. clear_errors - Alte Error-Logs löschen (VOR mark_complete wenn Fehler behoben)

═══════════════════════════════════════════════════════════════════════════════
              ✨ E1 QUALITY STANDARDS
═══════════════════════════════════════════════════════════════════════════════

CODE QUALITÄT:
✓ Clean & lesbar
✓ Kommentiert (WARUM, nicht WAS)
✓ DRY (keine Wiederholungen)
✓ Defensive (Input-Validierung, Error-Handling)
✓ Performance-optimiert
✓ Security-bewusst
✓ VOLLSTÄNDIG (keine TODOs!)

TESTING QUALITÄT:
✓ Syntax Check (alle Dateien)
✓ Logic Validation (Dateien lesen)
✓ Preview Test (visuell!)
✓ Edge Cases getestet
✓ UX wie echter User
✓ Bei Spielen: Gameplay getestet

DELIVERY QUALITÄT:
✓ Produktions-ready
✓ Keine Bugs
✓ Alle Features implementiert
✓ Gut getestet
✓ Dokumentiert (wo nötig)

═══════════════════════════════════════════════════════════════════════════════
              🎯 DEIN ZIEL
═══════════════════════════════════════════════════════════════════════════════

Arbeite GENAU WIE E1 bei app.emergent.sh:
• Frage BEVOR du implementierst
• Recherchiere BEVOR du codest
• Denke BEVOR du handelst
• Teste GRÜNDLICH
• Liefere QUALITÄT

DU BIST E1 - HANDLE WIE E1!

Antworte auf Deutsch."""

    messages = [{"role": "system", "content": system_prompt}] + initial_messages
    iteration = 0
    should_continue = True
    
    # Determine which LLM to use
    active_provider = get_active_llm_provider()
    logger.info(f"Using LLM provider: {active_provider}")
    
    while should_continue:
        iteration += 1
        
        # Safety valve - but with warning, not hard stop
        if iteration > max_iterations:
            yield f"data: {json.dumps({'warning': f'Iteration {iteration} erreicht - prüfe ob wirklich fertig', 'iteration': iteration})}\n\n"
            # Don't stop immediately - give agent chance to finish
            if iteration > max_iterations + 20:
                yield f"data: {json.dumps({'error': 'Max iterations (200+20) erreicht - Force Stop', 'iteration': iteration})}\n\n"
                should_continue = False
                break
        
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
                        error_msg = "Ollama fehlgeschlagen, nutze OpenAI"
                        await add_log(project_id, "warning", error_msg, "orchestrator")
                        yield f"data: {json.dumps({'warning': error_msg, 'provider': 'openai'})}\n\n"
                        # DON'T set should_continue = False! Just switch provider and continue!
                    else:
                        error_msg = "Kein LLM verfügbar"
                        await add_log(project_id, "error", error_msg, "orchestrator")
                        yield f"data: {json.dumps({'error': error_msg})}\n\n"
                        should_continue = False
                        break
            else:
                # Use OpenAI
                if not openai_client:
                    error_msg = "Kein OpenAI API Key konfiguriert. Bitte unter Einstellungen > API Keys hinzufügen."
                    await add_log(project_id, "error", error_msg, "orchestrator")
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
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
                
                # Build assistant message properly
                assistant_msg = {"role": "assistant", "content": content}
                
                # CRITICAL: Only add tool_calls if there are actual tool calls
                # Empty tool_calls array is INVALID for OpenAI API
                if tool_calls:
                    assistant_msg["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in tool_calls
                    ]
                
                messages.append(assistant_msg)
                
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
                
                # If no tool calls and not stopping, FORCE agent to continue (like E1!)
                if not tool_calls and not stop_this_iteration:
                    # E1 STRATEGY: Add thinking prompt to force continuation
                    if content:
                        # Agent provided content but no tools - nudge it to take action
                        messages.append({
                            "role": "user", 
                            "content": """Du hast nachgedacht, aber keine Tools genutzt. 

JETZT HANDELN! Nutze Tools um fortzufahren:
- Erstelle Dateien (create_file)
- Teste Code (test_code)  
- Lese Dateien (read_file)
- Suche im Web (web_search)
- Stelle Fragen (ask_user) wenn unklar

STOPPE NICHT! Arbeite weiter bis mark_complete!"""
                        })
                    else:
                        # No content and no tools - something is wrong
                        messages.append({
                            "role": "user",
                            "content": "FEHLER: Keine Antwort und keine Tools! Bitte fortfahren mit der Arbeit!"
                        })
                    
                    # DON'T stop - loop will continue
                    continue
            
            await asyncio.sleep(0.5)
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Log specific error types
            if "429" in error_msg or "rate_limit" in error_msg.lower():
                detailed_error = f"⚠️ RATE LIMIT: OpenAI API zu viele Anfragen. Bitte warte kurz."
                await add_log(project_id, "error", detailed_error, "orchestrator")
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                detailed_error = f"❌ API KEY FEHLER: OpenAI API Key ungültig. Bitte in Einstellungen prüfen."
                await add_log(project_id, "error", detailed_error, "orchestrator")
            elif "timeout" in error_msg.lower():
                detailed_error = f"⏱️ TIMEOUT: OpenAI API Zeitüberschreitung."
                await add_log(project_id, "error", detailed_error, "debugger")
            else:
                detailed_error = f"❌ FEHLER: {error_type}: {error_msg[:200]}"
                await add_log(project_id, "error", detailed_error, "debugger")
            
            logger.error(f"Error in autonomous agent loop (iteration {iteration}): {e}")
            yield f"data: {json.dumps({'error': f'Agent Error: {error_msg[:100]}', 'iteration': iteration})}\n\n"
            
            # E1 STRATEGY: Don't stop on error - try to recover!
            messages.append({
                "role": "user",
                "content": f"FEHLER aufgetreten: {error_msg}\n\nBitte analysiere den Fehler und fahre fort! Nutze debug_error wenn nötig."
            })
            # Continue loop to let agent recover
    
    # Final summary
    if iteration >= max_iterations + 20:
        yield f"data: {json.dumps({'done': True, 'iterations': iteration, 'status': 'max_iterations_reached'})}\n\n"
    else:
        yield f"data: {json.dumps({'done': True, 'iterations': iteration, 'status': 'completed'})}\n\n"

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
async def get_projects(include_archived: bool = False):
    """Get all projects, optionally including archived ones"""
    query = {} if include_archived else {"archived": {"$ne": True}}
    return await db.projects.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)

@api_router.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: str):
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@api_router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project completely"""
    try:
        # Delete from database first
        await db.projects.delete_one({"id": project_id})
        await db.messages.delete_many({"project_id": project_id})
        await db.agent_status.delete_many({"project_id": project_id})
        await db.roadmap.delete_many({"project_id": project_id})
        await db.logs.delete_many({"project_id": project_id})
        
        # Delete workspace folder
        workspace_path = WORKSPACES_DIR / project_id
        if workspace_path.exists():
            shutil.rmtree(workspace_path)
        
        return {"success": True, "message": f"Projekt {project_id} gelöscht"}
    except Exception as e:
        logger.error(f"Delete project error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/projects/{project_id}/download")
async def download_project(project_id: str):
    """Download project as ZIP file"""
    try:
        from fastapi.responses import FileResponse
        import zipfile
        
        workspace_path = Path(f"/app/workspaces/{project_id}")
        if not workspace_path.exists():
            raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
        
        # Create ZIP file
        zip_path = Path(f"/tmp/{project_id}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in workspace_path.rglob("*"):
                if file.is_file() and not any(part.startswith('.') for part in file.parts):
                    arcname = file.relative_to(workspace_path)
                    zipf.write(file, arcname)
        
        return FileResponse(
            path=str(zip_path),
            media_type="application/zip",
            filename=f"project_{project_id}.zip"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download project error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/projects/{project_id}/archive")
async def archive_project(project_id: str):
    """Archive a completed project"""
    try:
        result = await db.projects.update_one(
            {"id": project_id},
            {"$set": {
                "archived": True,
                "archived_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
        
        return {"success": True, "message": "Projekt archiviert"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Archive project error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/projects/archived/list")
async def get_archived_projects():
    """Get all archived projects"""
    try:
        projects = await db.projects.find(
            {"archived": True}, 
            {"_id": 0}
        ).sort("archived_at", -1).to_list(100)
        return projects
    except Exception as e:
        logger.error(f"Get archived projects error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/projects/{project_id}/unarchive")
async def unarchive_project(project_id: str):
    """Restore an archived project"""
    try:
        result = await db.projects.update_one(
            {"id": project_id},
            {"$unset": {"archived": "", "archived_at": ""}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
        
        return {"success": True, "message": "Projekt wiederhergestellt"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unarchive project error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

    # --- RE-OPEN-Logik: Wenn das Projekt als "fertig" markiert war und User erneut schreibt,
    #     öffnen wir es wieder als weitere Iteration. Ohne das würde der Agent
    #     in der History "✅ PROJEKT FERTIG!" sehen und neue Anforderungen ignorieren. ---
    reopened = False
    previous_status = project.get("status")
    if previous_status in ("ready_for_push", "completed", "done"):
        await db.projects.update_one(
            {"id": project_id},
            {
                "$set": {
                    "status": "iterating",
                    "pending_commit_message": None,
                },
                "$inc": {"iteration_count": 1},
            },
        )
        reopened = True
        await add_log(
            project_id,
            "info",
            f"🔄 Neue User-Anforderung nach Fertig-Status ('{previous_status}'). Projekt wird fortgeführt.",
            "orchestrator",
        )
        # Eine System-Message in den History-Stream setzen, damit der Agent versteht:
        # das Projekt war fertig, es gibt aber eine neue Anforderung.
        iteration_note = Message(
            project_id=project_id,
            content=(
                "⚡️ Neue Iteration: Das Projekt war bereits als fertig markiert, aber der "
                "Nutzer hat eine neue Anforderung geschickt. Ignoriere vorherige 'Projekt "
                "fertig'-Signale und arbeite die neue Anforderung vollständig um. Rufe "
                "mark_complete erst wieder auf, wenn auch diese neue Anforderung "
                "implementiert, getestet und verifiziert ist."
            ),
            role="system",
            agent_type="orchestrator",
        )
        await db.messages.insert_one(iteration_note.model_dump())

    # --- DELIVERY LAYER: Job laden/erstellen + Approval-Keywords prüfen ---
    active_job = await delivery_orchestrator.get_active_job(project_id)
    if active_job is None or reopened:
        # Re-open: neuen Job anlegen, damit Stage-Machine sauber startet
        job_id = await delivery_orchestrator.create_job(
            project_id=project_id,
            session_id=project_id,
            user_id=project.get("owner") or project.get("user_id"),
            request_text=message.content,
        )
        active_job = await delivery_orchestrator.get_job(job_id)

    # Wenn Job auf Freigabe wartet, User-Nachricht nach Approval/Reject parsen
    approval_signal = None
    if active_job and active_job["stage"] == DeliveryStage.AWAITING_APPROVAL.value:
        approval_signal = DeliveryOrchestrator.detect_approval(message.content)
        if approval_signal is True:
            try:
                active_job = await delivery_orchestrator.set_approval(
                    active_job["job_id"],
                    approved=True,
                    approved_by=project.get("owner") or "chat_user",
                    reason="Chat-Freigabe",
                )
                await delivery_orchestrator.append_log(
                    active_job["job_id"], "info", "User hat via Chat freigegeben."
                )
                # Deploy-Trigger schreiben (wird von updater-service.sh verarbeitet)
                try:
                    _write_deploy_trigger(project_id, active_job["job_id"])
                    await delivery_orchestrator.append_log(
                        active_job["job_id"], "info", "Deploy-Trigger erstellt."
                    )
                except Exception as e:
                    await delivery_orchestrator.append_log(
                        active_job["job_id"], "error", f"Deploy-Trigger-Fehler: {e}"
                    )
            except Exception as e:
                logger.error(f"Approval-Flow-Fehler: {e}")
        elif approval_signal is False:
            try:
                active_job = await delivery_orchestrator.set_approval(
                    active_job["job_id"],
                    approved=False,
                    approved_by=project.get("owner") or "chat_user",
                    reason=f"User-Ablehnung: {message.content[:200]}",
                )
            except Exception as e:
                logger.error(f"Reject-Flow-Fehler: {e}")

    history = await db.messages.find({"project_id": project_id}, {"_id": 0}).sort("created_at", 1).to_list(20)
    messages_for_api = [{"role": msg["role"], "content": msg["content"]} for msg in history[-15:]]
    
    async def generate():
        full_response = ""
        files_created = []
        
        await update_agent(project_id, "orchestrator", "running", "Starte autonome Entwicklung...")
        yield f"data: {json.dumps({'agent': 'orchestrator', 'status': 'running', 'autonomous': True, 'provider': get_active_llm_provider(), 'delivery_job_id': active_job.get('job_id') if active_job else None, 'delivery_stage': active_job.get('stage') if active_job else None})}\n\n"
        
        async for chunk in run_autonomous_agent(project_id, workspace_path, messages_for_api):
            yield chunk
            
            if chunk.startswith('data: '):
                try:
                    data = json.loads(chunk[6:])
                    if 'content' in data:
                        full_response += data['content']
                except:
                    pass

        # Delivery-Meta aus Agent-Response extrahieren + Stage updaten
        delivery_meta = _extract_delivery_meta(full_response)
        clean_response = _strip_delivery_meta(full_response)
        if delivery_meta and active_job:
            try:
                await _apply_delivery_meta(active_job["job_id"], delivery_meta)
                # Aktuellen Stand des Jobs mitschicken an UI
                updated = await delivery_orchestrator.get_job(active_job["job_id"])
                yield f"data: {json.dumps({'delivery_update': True, 'job': updated})}\n\n"
            except Exception as e:
                logger.error(f"Delivery-Meta-Apply-Fehler: {e}")

        if clean_response:
            ai_msg = Message(project_id=project_id, content=clean_response, role="assistant", agent_type="orchestrator")
            await db.messages.insert_one(ai_msg.model_dump())
        
        await update_agent(project_id, "orchestrator", "completed", "Fertig")
    
    return StreamingResponse(generate(), media_type="text/event-stream")


# ============== DELIVERY LAYER HELPERS ==============

_DELIVERY_META_RE = re.compile(
    r"---DELIVERY_META---\s*(?P<body>\{.*?\})\s*---END_DELIVERY_META---",
    re.DOTALL,
)


def _extract_delivery_meta(text: str) -> Optional[dict]:
    """Parst den letzten DELIVERY_META-Block aus dem Agent-Output."""
    if not text:
        return None
    matches = list(_DELIVERY_META_RE.finditer(text))
    if not matches:
        return None
    body = matches[-1].group("body")
    try:
        return json.loads(body)
    except Exception as e:
        logger.warning(f"DELIVERY_META JSON parse failed: {e}")
        return None


def _strip_delivery_meta(text: str) -> str:
    if not text:
        return text
    return _DELIVERY_META_RE.sub("", text).strip()


async def _apply_delivery_meta(job_id: str, meta: dict):
    """Überträgt Felder aus dem DELIVERY_META in den Orchestrator-Zustand."""
    stage_raw = (meta.get("stage") or "").strip().lower()
    if not stage_raw:
        return

    try:
        stage = DeliveryStage(stage_raw)
    except ValueError:
        logger.warning(f"Unbekannte stage '{stage_raw}' im DELIVERY_META, ignoriere.")
        return

    current = await delivery_orchestrator.get_job(job_id)
    if not current:
        return

    update_meta = {
        k: v for k, v in {
            "summary": meta.get("summary"),
            "deploy_plan": meta.get("deploy_plan"),
            "verification_report": meta.get("verification_report"),
        }.items() if v is not None
    }

    # Preview-Spezial: set_preview erwartet URL
    preview_url = meta.get("preview_url")
    preview_checks = meta.get("preview_checks") or []

    needs_approval_flag = bool(meta.get("needs_approval"))

    try:
        # Sonderfälle, die eigene Methoden verlangen:
        if stage == DeliveryStage.PREVIEW_READY and preview_url:
            await delivery_orchestrator.set_preview(
                job_id, preview_url, checks=preview_checks, summary=meta.get("summary"),
            )
        elif stage == DeliveryStage.AWAITING_APPROVAL:
            await delivery_orchestrator.request_approval(
                job_id, summary=meta.get("summary"), deploy_plan=meta.get("deploy_plan"),
            )
        elif stage == DeliveryStage.DONE:
            await delivery_orchestrator.finalize_job(
                job_id,
                result=meta.get("verification_report") or {"summary": meta.get("summary")},
            )
        else:
            # Normale Stage-Transition (policy-engine respektieren)
            if current["stage"] != stage.value:
                try:
                    await delivery_orchestrator.update_stage(job_id, stage, meta=update_meta)
                except ValueError as ve:
                    # Invalid transition -> nur Metadaten updaten, Stage bleibt
                    logger.info(f"Stage-Transition ignoriert: {ve}")
                    if update_meta:
                        await delivery_orchestrator.coll.update_one(
                            {"job_id": job_id},
                            {"$set": {**update_meta, "updated_at": datetime.now(timezone.utc).isoformat()}},
                        )

        # Agent sagt "brauche Freigabe" ohne Stage-Wechsel: markieren
        if needs_approval_flag and stage != DeliveryStage.AWAITING_APPROVAL:
            await delivery_orchestrator.coll.update_one(
                {"job_id": job_id},
                {"$set": {"approval_required": True}},
            )
    except Exception as e:
        logger.error(f"_apply_delivery_meta Fehler: {e}")


def _write_deploy_trigger(project_id: str, job_id: str):
    """Schreibt Trigger-Datei, damit updater-service.sh den Deploy ausführt.

    Funktioniert mit dem bestehenden Update-Trigger-Mechanismus (vgl.
    /api/update/install). Datei-Pfad ist workspace-basiert, damit auch
    Nicht-Unraid-Hosts funktionieren.
    """
    candidates = [
        Path("/mnt/user/appdata/forgepilot/.deploy_trigger"),
        WORKSPACES_DIR / ".deploy_trigger",
    ]
    payload = {
        "project_id": project_id,
        "job_id": job_id,
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "action": "deploy_production",
    }
    written = False
    for p in candidates:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(payload, indent=2))
            logger.info(f"Deploy trigger geschrieben: {p}")
            written = True
        except Exception as e:
            logger.warning(f"Trigger {p} konnte nicht geschrieben werden: {e}")
    if not written:
        raise RuntimeError("Kein Trigger-Pfad beschreibbar.")


# ============== DELIVERY JOB REST API ==============

@api_router.get("/delivery/jobs/{project_id}")
async def get_delivery_jobs(project_id: str):
    """Liefert aktiven Job + Historie für ein Projekt."""
    active = await delivery_orchestrator.get_active_job(project_id)
    history = await delivery_orchestrator.list_jobs(project_id, limit=20)
    return {"active": active, "history": history}


@api_router.get("/delivery/job/{job_id}")
async def get_delivery_job(job_id: str):
    job = await delivery_orchestrator.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    return job


class ApprovalPayload(BaseModel):
    approved_by: Optional[str] = "ui_user"
    reason: Optional[str] = None


@api_router.post("/delivery/jobs/{job_id}/approve")
async def approve_delivery_job(job_id: str, payload: ApprovalPayload = Body(default=ApprovalPayload())):
    """Explizite Freigabe per UI-Button -> Stage DEPLOYING + Trigger-File."""
    job = await delivery_orchestrator.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    if job["stage"] != DeliveryStage.AWAITING_APPROVAL.value:
        raise HTTPException(
            status_code=409,
            detail=f"Job ist in Stage '{job['stage']}' – Freigabe nur in 'awaiting_approval' möglich.",
        )
    try:
        updated = await delivery_orchestrator.set_approval(
            job_id,
            approved=True,
            approved_by=payload.approved_by or "ui_user",
            reason=payload.reason or "UI-Freigabe",
        )
        try:
            _write_deploy_trigger(job["project_id"], job_id)
            await delivery_orchestrator.append_log(job_id, "info", "Deploy-Trigger erstellt (UI-Freigabe).")
        except Exception as e:
            await delivery_orchestrator.append_log(job_id, "error", f"Deploy-Trigger-Fehler: {e}")
        return {"success": True, "job": updated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api_router.post("/delivery/jobs/{job_id}/reject")
async def reject_delivery_job(job_id: str, payload: ApprovalPayload = Body(default=ApprovalPayload())):
    job = await delivery_orchestrator.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    try:
        updated = await delivery_orchestrator.set_approval(
            job_id,
            approved=False,
            approved_by=payload.approved_by or "ui_user",
            reason=payload.reason or "UI-Ablehnung",
        )
        return {"success": True, "job": updated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api_router.post("/delivery/jobs/{job_id}/evaluate-action")
async def evaluate_action_endpoint(job_id: str, action: str = Body(..., embed=True)):
    """Policy-Check für Tools/Aktionen (z.B. vor Deploy)."""
    decision = policy_evaluate(action)
    return decision.to_dict()

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
        # Try common build output directories for React/Vue/Vite apps
        for entry in ["index.html", "build/index.html", "dist/index.html", "public/index.html"]:
            if (workspace / entry).exists():
                target_path = workspace / entry
                break
    
    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"Preview file not found. Tried: index.html, build/index.html, dist/index.html, public/index.html")
    
    content_types = {".html": "text/html", ".css": "text/css", ".js": "application/javascript", ".json": "application/json", ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml"}
    return FileResponse(target_path, media_type=content_types.get(target_path.suffix.lower(), "text/plain"))

@api_router.get("/projects/{project_id}/preview-info")
async def get_preview_info(project_id: str):
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    workspace = Path(project.get('workspace_path', WORKSPACES_DIR / project_id))
    entry_point = None
    for ep in ["build/index.html", "dist/index.html", "index.html", "public/index.html"]:
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

# Include API v1 Routers (NEW MODULE SYSTEM)
try:
    from api.v1 import settings as settings_api
    app.include_router(settings_api.router, prefix="/api/v1")
    logger.info("✅ API v1 Settings Router loaded")
except Exception as e:
    logger.warning(f"⚠️  API v1 Settings Router not available: {e}")

# Include legacy router
app.include_router(api_router)

app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("shutdown")
async def shutdown():
    client.close()
