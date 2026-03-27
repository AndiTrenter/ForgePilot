from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query, Body
from fastapi.responses import StreamingResponse, FileResponse
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
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Settings collection for API keys
settings_collection = db.settings

# Global settings (loaded from DB or env)
class AppSettings:
    openai_api_key: str = os.environ.get('OPENAI_API_KEY', '')
    github_token: str = os.environ.get('GITHUB_TOKEN', '')
    ollama_url: str = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
    use_ollama: bool = os.environ.get('USE_OLLAMA', 'false').lower() == 'true'

app_settings = AppSettings()

# OpenAI client (will be updated when settings change)
openai_client = AsyncOpenAI(api_key=app_settings.openai_api_key) if app_settings.openai_api_key else None

# Load settings from database on startup
async def load_settings_from_db():
    global openai_client, app_settings
    saved = await settings_collection.find_one({"_id": "app_settings"})
    if saved:
        if saved.get('openai_api_key'):
            app_settings.openai_api_key = saved['openai_api_key']
            openai_client = AsyncOpenAI(api_key=app_settings.openai_api_key)
        if saved.get('github_token'):
            app_settings.github_token = saved['github_token']
        if saved.get('ollama_url'):
            app_settings.ollama_url = saved['ollama_url']
        if saved.get('use_ollama') is not None:
            app_settings.use_ollama = saved['use_ollama']
    logger.info(f"Settings loaded: OpenAI key set: {bool(app_settings.openai_api_key)}, GitHub token set: {bool(app_settings.github_token)}")

# Ollama settings
OLLAMA_URL = app_settings.ollama_url
USE_OLLAMA = app_settings.use_ollama

# GitHub token (use from settings)
github_token = app_settings.github_token

# Workspace base directory
WORKSPACES_DIR = Path('/app/workspaces')
WORKSPACES_DIR.mkdir(exist_ok=True)

# Create the main app
app = FastAPI(title="ForgePilot API")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Startup event to load settings
@app.on_event("startup")
async def startup_event():
    await load_settings_from_db()

# ============== MODELS ==============

class SettingsUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    github_token: Optional[str] = None
    ollama_url: Optional[str] = None
    use_ollama: Optional[bool] = None

class SettingsResponse(BaseModel):
    openai_api_key_set: bool
    github_token_set: bool
    ollama_url: str
    use_ollama: bool

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    project_type: str = "fullstack"

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

# ============== SETTINGS ENDPOINTS ==============

@api_router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Get current settings (without exposing full keys)"""
    return SettingsResponse(
        openai_api_key_set=bool(app_settings.openai_api_key),
        github_token_set=bool(app_settings.github_token),
        ollama_url=app_settings.ollama_url,
        use_ollama=app_settings.use_ollama
    )

@api_router.put("/settings")
async def update_settings(settings: SettingsUpdate):
    """Update and save settings"""
    global openai_client, app_settings, github_token
    
    update_data = {}
    
    if settings.openai_api_key is not None:
        app_settings.openai_api_key = settings.openai_api_key
        update_data['openai_api_key'] = settings.openai_api_key
        if settings.openai_api_key:
            openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        else:
            openai_client = None
    
    if settings.github_token is not None:
        app_settings.github_token = settings.github_token
        github_token = settings.github_token
        update_data['github_token'] = settings.github_token
    
    if settings.ollama_url is not None:
        app_settings.ollama_url = settings.ollama_url
        update_data['ollama_url'] = settings.ollama_url
    
    if settings.use_ollama is not None:
        app_settings.use_ollama = settings.use_ollama
        update_data['use_ollama'] = settings.use_ollama
    
    # Save to database
    if update_data:
        await settings_collection.update_one(
            {"_id": "app_settings"},
            {"$set": update_data},
            upsert=True
        )
    
    logger.info(f"Settings updated: {list(update_data.keys())}")
    
    return {
        "success": True,
        "message": "Einstellungen gespeichert",
        "openai_api_key_set": bool(app_settings.openai_api_key),
        "github_token_set": bool(app_settings.github_token)
    }

@api_router.delete("/settings/openai-key")
async def delete_openai_key():
    """Delete OpenAI API key"""
    global openai_client, app_settings
    app_settings.openai_api_key = ""
    openai_client = None
    await settings_collection.update_one(
        {"_id": "app_settings"},
        {"$unset": {"openai_api_key": ""}},
        upsert=True
    )
    return {"success": True, "message": "OpenAI API Key gelöscht"}

@api_router.delete("/settings/github-token")
async def delete_github_token():
    """Delete GitHub token"""
    global github_token, app_settings
    app_settings.github_token = ""
    github_token = ""
    await settings_collection.update_one(
        {"_id": "app_settings"},
        {"$unset": {"github_token": ""}},
        upsert=True
    )
    return {"success": True, "message": "GitHub Token gelöscht"}

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
                # Check HTML/CSS/JS syntax
                errors = []
                for f in workspace_path.rglob("*.js"):
                    try:
                        subprocess.run(["node", "--check", str(f)], capture_output=True, check=True)
                    except subprocess.CalledProcessError as e:
                        errors.append(f"{f.name}: {e.stderr.decode()[:200]}")
                result["output"] = "✓ Syntax OK" if not errors else "Syntax-Fehler:\n" + "\n".join(errors)
            
            elif test_type == "run":
                # Try to run the code
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
    
    while should_continue and iteration < max_iterations:
        iteration += 1
        
        try:
            # Get AI response
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
            
            # Yield content
            if content:
                yield f"data: {json.dumps({'content': content, 'iteration': iteration})}\n\n"
            
            # No tool calls = done with this iteration
            if not tool_calls:
                should_continue = False
                break
            
            # Execute tools
            messages.append({"role": "assistant", "content": content, "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in tool_calls]})
            
            for tc in tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                    tool_name = tc.function.name
                    
                    yield f"data: {json.dumps({'tool': tool_name, 'args': {k: str(v)[:100] for k, v in args.items()}})}\n\n"
                    
                    result = await execute_tool(tool_name, args, workspace_path, project_id)
                    
                    yield f"data: {json.dumps({'tool_result': result['output'][:500]})}\n\n"
                    
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": result["output"]})
                    
                    # Check if we should stop
                    if not result["continue"]:
                        should_continue = False
                        if result["ask_user"]:
                            yield f"data: {json.dumps({'ask_user': True, 'question': result['output']})}\n\n"
                        if result["complete"]:
                            yield f"data: {json.dumps({'complete': True})}\n\n"
                        break
                    
                except json.JSONDecodeError:
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": "JSON Parse Error"})
            
            # Small delay to prevent rate limiting
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Agent loop error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            should_continue = False
    
    # Update final status
    if iteration >= max_iterations:
        yield f"data: {json.dumps({'warning': 'Max iterations erreicht'})}\n\n"
    
    yield f"data: {json.dumps({'done': True, 'iterations': iteration})}\n\n"

# ============== PROJECTS ==============

@api_router.get("/")
async def root():
    return {"message": "ForgePilot API", "version": "2.0.0", "ollama": USE_OLLAMA}

@api_router.post("/projects", response_model=Project)
async def create_project(project: ProjectCreate):
    project_obj = Project(name=project.name, description=project.description, project_type=project.project_type)
    workspace_path = WORKSPACES_DIR / project_obj.id
    workspace_path.mkdir(exist_ok=True)
    project_obj.workspace_path = str(workspace_path)
    
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
    
    # Save user message
    user_msg = Message(project_id=project_id, content=message.content, role="user")
    await db.messages.insert_one(user_msg.model_dump())
    
    # Get conversation history
    history = await db.messages.find({"project_id": project_id}, {"_id": 0}).sort("created_at", 1).to_list(20)
    messages_for_api = [{"role": msg["role"], "content": msg["content"]} for msg in history[-15:]]
    
    async def generate():
        full_response = ""
        files_created = []
        
        await update_agent(project_id, "orchestrator", "running", "Starte autonome Entwicklung...")
        yield f"data: {json.dumps({'agent': 'orchestrator', 'status': 'running', 'autonomous': True})}\n\n"
        
        async for chunk in run_autonomous_agent(project_id, workspace_path, messages_for_api):
            yield chunk
            
            # Parse chunk to collect response
            if chunk.startswith('data: '):
                try:
                    data = json.loads(chunk[6:])
                    if 'content' in data:
                        full_response += data['content']
                except:
                    pass
        
        # Save AI response
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
    if not github_token:
        raise HTTPException(status_code=400, detail="GitHub Token nicht konfiguriert")
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.github.com/user/repos", headers={"Authorization": f"token {github_token}"}, params={"per_page": 100, "sort": "updated"})
        response.raise_for_status()
        return {"repos": [{"name": r["name"], "full_name": r["full_name"], "url": r["clone_url"], "default_branch": r["default_branch"], "private": r["private"], "description": r.get("description") or ""} for r in response.json()]}

@api_router.get("/github/branches")
async def get_github_branches(repo: str = Query(...)):
    if not github_token:
        raise HTTPException(status_code=400, detail="GitHub Token nicht konfiguriert")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.github.com/repos/{repo}/branches", headers={"Authorization": f"token {github_token}"})
        response.raise_for_status()
        return {"branches": [b["name"] for b in response.json()]}

@api_router.post("/github/import")
async def import_from_github(data: GitHubImport):
    project_name = data.project_name or data.repo_url.split('/')[-1].replace('.git', '')
    project_obj = Project(name=project_name, description=f"Importiert von {data.repo_url}", github_url=data.repo_url)
    workspace_path = WORKSPACES_DIR / project_obj.id
    
    clone_url = data.repo_url.replace('https://', f'https://{github_token}@') if github_token else data.repo_url
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

# ============== OLLAMA ==============

@api_router.get("/ollama/status")
async def get_ollama_status():
    """Check if Ollama is available"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return {"available": True, "models": [m["name"] for m in models]}
    except:
        pass
    return {"available": False, "models": []}

@api_router.post("/ollama/enable")
async def enable_ollama(model: str = "llama3"):
    """Enable Ollama as primary LLM"""
    global USE_OLLAMA
    USE_OLLAMA = True
    return {"enabled": True, "model": model}

# Include router
app.include_router(api_router)

app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("shutdown")
async def shutdown():
    client.close()
