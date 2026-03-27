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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# OpenAI client
openai_client = AsyncOpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# GitHub token
github_token = os.environ.get('GITHUB_TOKEN', '')

# Workspace base directory
WORKSPACES_DIR = Path('/app/workspaces')
WORKSPACES_DIR.mkdir(exist_ok=True)

# Create the main app
app = FastAPI(title="ForgePilot API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============== MODELS ==============

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
    preview_port: Optional[int] = None

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
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

class GitHubImport(BaseModel):
    repo_url: str
    branch: str = "main"
    project_name: Optional[str] = None

class GitHubCommit(BaseModel):
    project_id: str
    message: str
    branch: Optional[str] = "main"

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

class FileContent(BaseModel):
    path: str
    content: str

class FileCreate(BaseModel):
    path: str
    content: str

# ============== HELPER FUNCTIONS ==============

async def add_log(project_id: str, level: str, message: str, source: str = "system"):
    """Helper to add log entries"""
    log = LogEntry(project_id=project_id, level=level, message=message, source=source)
    await db.logs.insert_one(log.model_dump())
    return log

async def update_agent(project_id: str, agent_type: str, status: str, message: str = None):
    """Helper to update agent status"""
    update_data = {"status": status, "message": message}
    if status == "running":
        update_data["started_at"] = datetime.now(timezone.utc).isoformat()
        update_data["completed_at"] = None
    elif status in ["completed", "error", "idle"]:
        update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.agent_status.update_one(
        {"project_id": project_id, "agent_type": agent_type},
        {"$set": update_data},
        upsert=True
    )

def get_file_tree(workspace_path: Path, prefix: str = "") -> List[Dict]:
    """Get file tree structure"""
    items = []
    try:
        for item in sorted(workspace_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            if item.name.startswith('.') or item.name in ['node_modules', '__pycache__', 'venv', '.git']:
                continue
            
            rel_path = f"{prefix}/{item.name}" if prefix else item.name
            
            if item.is_dir():
                items.append({
                    "name": item.name,
                    "type": "directory",
                    "path": rel_path,
                    "children": get_file_tree(item, rel_path)
                })
            else:
                items.append({
                    "name": item.name,
                    "type": "file",
                    "path": rel_path
                })
    except Exception as e:
        logger.error(f"Error getting file tree: {e}")
    return items

# ============== OPENAI TOOLS DEFINITION ==============

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a new file with the specified content in the project workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The file path relative to the project root (e.g., 'src/App.js', 'index.html')"
                    },
                    "content": {
                        "type": "string",
                        "description": "The complete content of the file"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modify_file",
            "description": "Modify an existing file by replacing its content",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The file path relative to the project root"
                    },
                    "content": {
                        "type": "string",
                        "description": "The new complete content of the file"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the content of an existing file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The file path relative to the project root"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file from the project workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The file path relative to the project root"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List all files in the project workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Optional directory path to list (defaults to root)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command in the project workspace (e.g., npm install, python script.py)",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_roadmap",
            "description": "Create a roadmap item for the project plan",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the roadmap item"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of what needs to be done"
                    }
                },
                "required": ["title", "description"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "update_roadmap_status",
            "description": "Update the status of a roadmap item",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the roadmap item to update"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed"],
                        "description": "New status"
                    }
                },
                "required": ["title", "status"]
            }
        }
    }
]

async def execute_tool(tool_name: str, arguments: dict, workspace_path: Path, project_id: str) -> str:
    """Execute a tool and return the result"""
    try:
        if tool_name == "create_file":
            file_path = workspace_path / arguments["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(arguments["content"])
            await add_log(project_id, "success", f"Datei erstellt: {arguments['path']}", "coder")
            return f"Datei erfolgreich erstellt: {arguments['path']}"
        
        elif tool_name == "modify_file":
            file_path = workspace_path / arguments["path"]
            if not file_path.exists():
                return f"Fehler: Datei nicht gefunden: {arguments['path']}"
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(arguments["content"])
            await add_log(project_id, "success", f"Datei geändert: {arguments['path']}", "coder")
            return f"Datei erfolgreich geändert: {arguments['path']}"
        
        elif tool_name == "read_file":
            file_path = workspace_path / arguments["path"]
            if not file_path.exists():
                return f"Fehler: Datei nicht gefunden: {arguments['path']}"
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
            return f"Inhalt von {arguments['path']}:\n```\n{content}\n```"
        
        elif tool_name == "delete_file":
            file_path = workspace_path / arguments["path"]
            if file_path.exists():
                file_path.unlink()
                await add_log(project_id, "info", f"Datei gelöscht: {arguments['path']}", "coder")
                return f"Datei gelöscht: {arguments['path']}"
            return f"Datei nicht gefunden: {arguments['path']}"
        
        elif tool_name == "list_files":
            directory = arguments.get("directory", "")
            target_path = workspace_path / directory if directory else workspace_path
            if not target_path.exists():
                return f"Verzeichnis nicht gefunden: {directory}"
            
            files = []
            for item in target_path.rglob("*"):
                if item.is_file() and not any(p in str(item) for p in ['.git', 'node_modules', '__pycache__']):
                    files.append(str(item.relative_to(workspace_path)))
            return f"Dateien im Projekt:\n" + "\n".join(files[:50])
        
        elif tool_name == "run_command":
            command = arguments["command"]
            # Security: Only allow safe commands
            safe_commands = ['npm', 'yarn', 'pip', 'python', 'node', 'cat', 'ls', 'mkdir', 'echo']
            cmd_parts = command.split()
            if not any(command.startswith(safe) for safe in safe_commands):
                return f"Befehl nicht erlaubt aus Sicherheitsgründen: {command}"
            
            await add_log(project_id, "info", f"Befehl ausführen: {command}", "tester")
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                output = result.stdout + result.stderr
                if result.returncode == 0:
                    await add_log(project_id, "success", f"Befehl erfolgreich: {command}", "tester")
                else:
                    await add_log(project_id, "error", f"Befehl fehlgeschlagen: {command}", "tester")
                return f"Befehl: {command}\nExit Code: {result.returncode}\nAusgabe:\n{output[:2000]}"
            except subprocess.TimeoutExpired:
                return f"Befehl Timeout nach 60 Sekunden: {command}"
        
        elif tool_name == "create_roadmap":
            last_item = await db.roadmap.find_one({"project_id": project_id}, sort=[("order", -1)])
            next_order = (last_item.get("order", 0) + 1) if last_item else 0
            
            item = RoadmapItem(
                project_id=project_id,
                title=arguments["title"],
                description=arguments["description"],
                order=next_order
            )
            await db.roadmap.insert_one(item.model_dump())
            await add_log(project_id, "info", f"Roadmap erstellt: {arguments['title']}", "planner")
            return f"Roadmap-Eintrag erstellt: {arguments['title']}"
        
        elif tool_name == "update_roadmap_status":
            result = await db.roadmap.update_one(
                {"project_id": project_id, "title": arguments["title"]},
                {"$set": {"status": arguments["status"]}}
            )
            if result.modified_count > 0:
                return f"Roadmap-Status aktualisiert: {arguments['title']} -> {arguments['status']}"
            return f"Roadmap-Eintrag nicht gefunden: {arguments['title']}"
        
        return f"Unbekanntes Tool: {tool_name}"
    
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        await add_log(project_id, "error", f"Tool-Fehler: {str(e)}", "debugger")
        return f"Fehler bei {tool_name}: {str(e)}"

# ============== PROJECTS ==============

@api_router.get("/")
async def root():
    return {"message": "ForgePilot API", "version": "1.0.0"}

@api_router.post("/projects", response_model=Project)
async def create_project(project: ProjectCreate):
    project_obj = Project(
        name=project.name,
        description=project.description,
        project_type=project.project_type
    )
    
    # Create workspace directory
    workspace_path = WORKSPACES_DIR / project_obj.id
    workspace_path.mkdir(exist_ok=True)
    project_obj.workspace_path = str(workspace_path)
    
    # Create initial files based on project type
    if project.project_type == "fullstack":
        # Create a basic project structure
        (workspace_path / "src").mkdir(exist_ok=True)
        (workspace_path / "public").mkdir(exist_ok=True)
    
    doc = project_obj.model_dump()
    await db.projects.insert_one(doc)
    
    # Initialize agent statuses
    for agent_type in ["orchestrator", "planner", "coder", "reviewer", "tester", "debugger", "git"]:
        agent = AgentStatus(project_id=project_obj.id, agent_type=agent_type, status="idle")
        await db.agent_status.insert_one(agent.model_dump())
    
    await add_log(project_obj.id, "success", f"Projekt erstellt: {project.name}", "system")
    
    return project_obj

@api_router.get("/projects", response_model=List[Project])
async def get_projects():
    projects = await db.projects.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return projects

@api_router.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: str):
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@api_router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    await db.projects.delete_one({"id": project_id})
    
    # Delete workspace
    workspace_path = WORKSPACES_DIR / project_id
    if workspace_path.exists():
        shutil.rmtree(workspace_path)
    
    # Delete related data
    await db.messages.delete_many({"project_id": project_id})
    await db.agent_status.delete_many({"project_id": project_id})
    await db.roadmap.delete_many({"project_id": project_id})
    await db.logs.delete_many({"project_id": project_id})
    
    return {"message": "Project deleted"}

# ============== MESSAGES / CHAT ==============

@api_router.get("/projects/{project_id}/messages", response_model=List[Message])
async def get_messages(project_id: str):
    messages = await db.messages.find(
        {"project_id": project_id}, 
        {"_id": 0}
    ).sort("created_at", 1).to_list(1000)
    return messages

@api_router.post("/projects/{project_id}/messages", response_model=Message)
async def create_message(project_id: str, message: MessageCreate):
    """Create a new message directly"""
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    msg_obj = Message(
        project_id=project_id,
        content=message.content,
        role=message.role
    )
    await db.messages.insert_one(msg_obj.model_dump())
    return msg_obj

@api_router.post("/projects/{project_id}/chat")
async def chat_with_ai(project_id: str, message: MessageCreate):
    """Send a message and get AI response with streaming and tool execution"""
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    workspace_path = Path(project.get('workspace_path', WORKSPACES_DIR / project_id))
    workspace_path.mkdir(exist_ok=True)
    
    # Save user message
    user_msg = Message(
        project_id=project_id,
        content=message.content,
        role="user"
    )
    await db.messages.insert_one(user_msg.model_dump())
    
    # Get conversation history
    history = await db.messages.find(
        {"project_id": project_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(30)
    
    # Get current files in workspace
    file_list = []
    try:
        for item in workspace_path.rglob("*"):
            if item.is_file() and not any(p in str(item) for p in ['.git', 'node_modules', '__pycache__']):
                file_list.append(str(item.relative_to(workspace_path)))
    except:
        pass
    
    files_context = "\n".join(file_list[:30]) if file_list else "Keine Dateien vorhanden"
    
    # Build system prompt
    system_prompt = f"""Du bist ForgePilot, ein fortschrittlicher KI-Entwicklungsassistent. Du kannst vollständige Softwareprojekte erstellen, Code schreiben und Dateien verwalten.

PROJEKT-INFORMATIONEN:
- Name: {project.get('name', 'Unbenannt')}
- Beschreibung: {project.get('description', 'Keine Beschreibung')}
- Typ: {project.get('project_type', 'fullstack')}
- Workspace: {workspace_path}

AKTUELLE DATEIEN IM PROJEKT:
{files_context}

DEINE FÄHIGKEITEN:
1. Dateien erstellen und bearbeiten (create_file, modify_file)
2. Dateien lesen und auflisten (read_file, list_files)
3. Befehle ausführen (run_command) - z.B. npm install, pip install
4. Roadmap erstellen und verwalten (create_roadmap, update_roadmap_status)

ARBEITSWEISE:
1. Analysiere die Anforderungen des Nutzers
2. Erstelle einen Plan (Roadmap)
3. Implementiere die Lösung schrittweise
4. Erstelle alle notwendigen Dateien
5. Erkläre was du tust

WICHTIG:
- Erstelle immer vollständige, funktionsfähige Dateien
- Bei Web-Projekten: Erstelle index.html, styles.css, und app.js
- Bei React-Projekten: Erstelle die komplette Projektstruktur
- Antworte auf Deutsch
- Zeige dem Nutzer den erstellten Code"""

    messages_for_api = [{"role": "system", "content": system_prompt}]
    for msg in history[-20:]:
        messages_for_api.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })
    
    async def generate():
        files_created = []
        files_modified = []
        full_response = ""
        
        try:
            # Update agent status
            await update_agent(project_id, "orchestrator", "running", "Verarbeite Anfrage...")
            yield f"data: {json.dumps({'agent': 'orchestrator', 'status': 'running'})}\n\n"
            
            # First API call
            response = await openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages_for_api,
                tools=AGENT_TOOLS,
                tool_choice="auto",
                stream=True,
                max_tokens=4000
            )
            
            tool_calls = []
            current_tool_call = None
            
            async for chunk in response:
                delta = chunk.choices[0].delta
                
                # Handle content
                if delta.content:
                    full_response += delta.content
                    yield f"data: {json.dumps({'content': delta.content})}\n\n"
                
                # Handle tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.index is not None:
                            while len(tool_calls) <= tc.index:
                                tool_calls.append({"id": "", "function": {"name": "", "arguments": ""}})
                            
                            if tc.id:
                                tool_calls[tc.index]["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    tool_calls[tc.index]["function"]["name"] = tc.function.name
                                if tc.function.arguments:
                                    tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments
            
            # Execute tool calls if any
            if tool_calls:
                await update_agent(project_id, "coder", "running", "Führe Aktionen aus...")
                yield f"data: {json.dumps({'agent': 'coder', 'status': 'running'})}\n\n"
                
                tool_results = []
                for tc in tool_calls:
                    if tc["function"]["name"] and tc["function"]["arguments"]:
                        try:
                            args = json.loads(tc["function"]["arguments"])
                            tool_name = tc["function"]["name"]
                            
                            yield f"data: {json.dumps({'tool': tool_name, 'args': args})}\n\n"
                            
                            result = await execute_tool(tool_name, args, workspace_path, project_id)
                            tool_results.append({
                                "tool_call_id": tc["id"],
                                "role": "tool",
                                "content": result
                            })
                            
                            if tool_name == "create_file":
                                files_created.append(args.get("path", ""))
                            elif tool_name == "modify_file":
                                files_modified.append(args.get("path", ""))
                            
                            yield f"data: {json.dumps({'tool_result': result[:500]})}\n\n"
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error: {e}")
                
                # Get final response after tool execution
                if tool_results:
                    messages_for_api.append({
                        "role": "assistant",
                        "content": full_response,
                        "tool_calls": [{"id": tc["id"], "type": "function", "function": tc["function"]} for tc in tool_calls if tc["id"]]
                    })
                    messages_for_api.extend(tool_results)
                    
                    # Get completion response
                    final_response = await openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=messages_for_api,
                        stream=True,
                        max_tokens=2000
                    )
                    
                    separator = "\n\n---\n\n"
                    yield f"data: {json.dumps({'content': separator})}\n\n"
                    full_response += separator
                    
                    async for chunk in final_response:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            full_response += content
                            yield f"data: {json.dumps({'content': content})}\n\n"
                
                await update_agent(project_id, "coder", "completed", "Aktionen abgeschlossen")
            
            # Update agents to completed
            await update_agent(project_id, "orchestrator", "completed", "Anfrage bearbeitet")
            
            # Save AI response
            ai_msg = Message(
                project_id=project_id,
                content=full_response,
                role="assistant",
                agent_type="orchestrator",
                files_created=files_created if files_created else None,
                files_modified=files_modified if files_modified else None
            )
            await db.messages.insert_one(ai_msg.model_dump())
            
            yield f"data: {json.dumps({'done': True, 'message_id': ai_msg.id, 'files_created': files_created, 'files_modified': files_modified})}\n\n"
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            await update_agent(project_id, "orchestrator", "error", str(e))
            await add_log(project_id, "error", f"Chat-Fehler: {str(e)}", "system")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

# ============== AGENT STATUS ==============

@api_router.get("/projects/{project_id}/agents", response_model=List[AgentStatus])
async def get_agent_statuses(project_id: str):
    agents = await db.agent_status.find(
        {"project_id": project_id},
        {"_id": 0}
    ).to_list(20)
    
    if not agents:
        default_agents = ["orchestrator", "planner", "coder", "reviewer", "tester", "debugger", "git"]
        for agent_type in default_agents:
            agent = AgentStatus(project_id=project_id, agent_type=agent_type, status="idle")
            await db.agent_status.insert_one(agent.model_dump())
            agents.append(agent.model_dump())
    
    return agents

@api_router.put("/projects/{project_id}/agents/{agent_type}")
async def update_agent_status_endpoint(project_id: str, agent_type: str, status: str = Query(...), message: Optional[str] = None):
    await update_agent(project_id, agent_type, status, message)
    return {"updated": True}

# ============== GITHUB OPERATIONS ==============

@api_router.get("/github/repos")
async def get_github_repos():
    """Get list of repositories from GitHub"""
    if not github_token:
        raise HTTPException(status_code=400, detail="GitHub Token nicht konfiguriert")
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user/repos",
                headers={
                    "Authorization": f"token {github_token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                params={"per_page": 100, "sort": "updated"}
            )
            response.raise_for_status()
            repos = response.json()
            
            return {
                "repos": [
                    {
                        "name": repo["name"],
                        "full_name": repo["full_name"],
                        "url": repo["clone_url"],
                        "default_branch": repo["default_branch"],
                        "private": repo["private"],
                        "description": repo.get("description") or ""
                    }
                    for repo in repos
                ]
            }
    except Exception as e:
        logger.error(f"GitHub repos error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/github/branches")
async def get_github_branches(repo: str = Query(...)):
    """Get branches for a repository"""
    if not github_token:
        raise HTTPException(status_code=400, detail="GitHub Token nicht konfiguriert")
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{repo}/branches",
                headers={
                    "Authorization": f"token {github_token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                params={"per_page": 100}
            )
            response.raise_for_status()
            branches = response.json()
            
            return {
                "branches": [branch["name"] for branch in branches]
            }
    except Exception as e:
        logger.error(f"GitHub branches error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@api_router.post("/github/import")
async def import_from_github(data: GitHubImport):
    """Clone a GitHub repository"""
    try:
        project_name = data.project_name or data.repo_url.split('/')[-1].replace('.git', '')
        project_obj = Project(
            name=project_name,
            description=f"Importiert von {data.repo_url}",
            github_url=data.repo_url,
            project_type="fullstack"
        )
        
        workspace_path = WORKSPACES_DIR / project_obj.id
        
        clone_url = data.repo_url
        if github_token and 'github.com' in clone_url:
            clone_url = clone_url.replace('https://', f'https://{github_token}@')
        
        git.Repo.clone_from(clone_url, workspace_path, branch=data.branch)
        
        project_obj.workspace_path = str(workspace_path)
        await db.projects.insert_one(project_obj.model_dump())
        
        # Initialize agents
        for agent_type in ["orchestrator", "planner", "coder", "reviewer", "tester", "debugger", "git"]:
            agent = AgentStatus(project_id=project_obj.id, agent_type=agent_type, status="idle")
            await db.agent_status.insert_one(agent.model_dump())
        
        await add_log(project_obj.id, "success", f"Repository geklont: {data.repo_url}", "git")
        
        return project_obj
        
    except Exception as e:
        logger.error(f"GitHub import error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@api_router.post("/github/commit")
async def commit_to_github(data: GitHubCommit):
    """Commit and push changes"""
    try:
        project = await db.projects.find_one({"id": data.project_id})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        workspace_path = project.get('workspace_path')
        if not workspace_path:
            raise HTTPException(status_code=400, detail="No workspace found")
        
        await update_agent(data.project_id, "git", "running", "Committing...")
        
        repo = git.Repo(workspace_path)
        repo.git.add(A=True)
        repo.index.commit(data.message)
        
        origin = repo.remote(name='origin')
        origin.push(data.branch)
        
        await update_agent(data.project_id, "git", "completed", "Push erfolgreich")
        await add_log(data.project_id, "success", f"Commit: {data.message}", "git")
        
        return {"success": True, "message": "Changes committed and pushed"}
        
    except Exception as e:
        await update_agent(data.project_id, "git", "error", str(e))
        logger.error(f"GitHub commit error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/github/branches/{project_id}")
async def get_branches(project_id: str):
    project = await db.projects.find_one({"id": project_id})
    if not project or not project.get('workspace_path'):
        raise HTTPException(status_code=404, detail="Project or workspace not found")
    
    try:
        repo = git.Repo(project['workspace_path'])
        branches = [ref.name for ref in repo.references if 'HEAD' not in ref.name]
        return {"branches": branches, "current": repo.active_branch.name}
    except:
        return {"branches": [], "current": None}

# ============== ROADMAP ==============

@api_router.get("/projects/{project_id}/roadmap", response_model=List[RoadmapItem])
async def get_roadmap(project_id: str):
    items = await db.roadmap.find(
        {"project_id": project_id},
        {"_id": 0}
    ).sort("order", 1).to_list(100)
    return items

@api_router.post("/projects/{project_id}/roadmap", response_model=RoadmapItem)
async def add_roadmap_item(project_id: str, data: dict = Body(...)):
    last_item = await db.roadmap.find_one({"project_id": project_id}, sort=[("order", -1)])
    next_order = (last_item.get("order", 0) + 1) if last_item else 0
    
    item = RoadmapItem(
        project_id=project_id,
        title=data.get("title", ""),
        description=data.get("description", ""),
        order=next_order
    )
    await db.roadmap.insert_one(item.model_dump())
    return item

@api_router.put("/projects/{project_id}/roadmap/{item_id}")
async def update_roadmap_item(project_id: str, item_id: str, data: dict = Body(...)):
    result = await db.roadmap.update_one(
        {"project_id": project_id, "id": item_id},
        {"$set": data}
    )
    return {"updated": result.modified_count > 0}

# ============== LOGS ==============

@api_router.get("/projects/{project_id}/logs", response_model=List[LogEntry])
async def get_logs(project_id: str, limit: int = 100):
    logs = await db.logs.find(
        {"project_id": project_id},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(limit)
    return logs

@api_router.post("/projects/{project_id}/logs", response_model=LogEntry)
async def add_log_entry(project_id: str, data: dict = Body(...)):
    log = await add_log(
        project_id, 
        data.get("level", "info"), 
        data.get("message", ""),
        data.get("source", "system")
    )
    return log

# ============== WORKSPACE FILES ==============

@api_router.get("/projects/{project_id}/files")
async def get_workspace_files(project_id: str, path: str = ""):
    """Get files in workspace directory"""
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    workspace = Path(project.get('workspace_path', WORKSPACES_DIR / project_id))
    if not workspace.exists():
        workspace.mkdir(parents=True, exist_ok=True)
    
    target_path = workspace / path if path else workspace
    
    if not target_path.exists():
        return {"type": "directory", "items": [], "tree": []}
    
    if target_path.is_file():
        try:
            async with aiofiles.open(target_path, 'r', errors='replace') as f:
                content = await f.read()
            return {"type": "file", "content": content, "path": path}
        except Exception as e:
            return {"type": "file", "content": f"Fehler beim Lesen: {e}", "path": path}
    
    # Return directory with tree structure
    tree = get_file_tree(workspace)
    
    items = []
    for item in target_path.iterdir():
        if item.name.startswith('.') or item.name in ['node_modules', '__pycache__']:
            continue
        items.append({
            "name": item.name,
            "type": "directory" if item.is_dir() else "file",
            "path": str(item.relative_to(workspace))
        })
    
    return {
        "type": "directory", 
        "items": sorted(items, key=lambda x: (x["type"] != "directory", x["name"])),
        "tree": tree
    }

@api_router.put("/projects/{project_id}/files")
async def save_workspace_file(project_id: str, data: FileCreate):
    """Save file in workspace"""
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    workspace = Path(project.get('workspace_path', WORKSPACES_DIR / project_id))
    target_path = workspace / data.path
    
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiofiles.open(target_path, 'w') as f:
        await f.write(data.content)
    
    await add_log(project_id, "info", f"Datei gespeichert: {data.path}", "editor")
    
    return {"success": True, "path": data.path}

@api_router.delete("/projects/{project_id}/files")
async def delete_workspace_file(project_id: str, path: str = Query(...)):
    """Delete file from workspace"""
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    workspace = Path(project.get('workspace_path', WORKSPACES_DIR / project_id))
    target_path = workspace / path
    
    if target_path.exists():
        if target_path.is_dir():
            shutil.rmtree(target_path)
        else:
            target_path.unlink()
        await add_log(project_id, "info", f"Gelöscht: {path}", "editor")
        return {"success": True}
    
    raise HTTPException(status_code=404, detail="File not found")

@api_router.post("/projects/{project_id}/files/new")
async def create_new_file(project_id: str, data: FileCreate):
    """Create a new file"""
    return await save_workspace_file(project_id, data)

# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
