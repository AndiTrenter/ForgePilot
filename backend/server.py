from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
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
    project_type: str = "fullstack"  # fullstack, mobile, landing

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

class AgentStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    agent_type: str  # orchestrator, planner, coder, reviewer, tester, debugger, git
    status: str = "idle"  # idle, running, completed, error
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
    status: str = "pending"  # pending, in_progress, completed
    order: int = 0

class LogEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    level: str  # info, warning, error, success
    message: str
    source: str = "system"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

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
    
    doc = project_obj.model_dump()
    await db.projects.insert_one(doc)
    return project_obj

@api_router.get("/projects", response_model=List[Project])
async def get_projects():
    projects = await db.projects.find({}, {"_id": 0}).to_list(100)
    return projects

@api_router.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: str):
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@api_router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    result = await db.projects.delete_one({"id": project_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    
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
    # Verify project exists
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    msg_obj = Message(
        project_id=project_id,
        content=message.content,
        role=message.role
    )
    
    doc = msg_obj.model_dump()
    await db.messages.insert_one(doc)
    return msg_obj

@api_router.post("/projects/{project_id}/chat")
async def chat_with_ai(project_id: str, message: MessageCreate):
    """Send a message and get AI response with streaming"""
    # Verify project exists
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
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
    ).sort("created_at", 1).to_list(50)
    
    # Build messages for OpenAI
    system_prompt = f"""Du bist ForgePilot, ein KI-Assistent für Softwareentwicklung. 
Du hilfst bei der Planung, Entwicklung und dem Debugging von Softwareprojekten.

Projekt: {project.get('name', 'Unbenannt')}
Beschreibung: {project.get('description', 'Keine Beschreibung')}
Typ: {project.get('project_type', 'fullstack')}

Deine Aufgaben:
1. Anforderungen verstehen und klären
2. Technische Strategien vorschlagen
3. Code generieren und erklären
4. Fehler analysieren und beheben
5. Best Practices empfehlen

Antworte auf Deutsch, es sei denn, der Nutzer schreibt auf einer anderen Sprache."""

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-20:]:  # Last 20 messages for context
        messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })
    
    async def generate():
        full_response = ""
        try:
            stream = await openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                stream=True,
                max_tokens=4000
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield f"data: {json.dumps({'content': content})}\n\n"
            
            # Save AI response
            ai_msg = Message(
                project_id=project_id,
                content=full_response,
                role="assistant",
                agent_type="orchestrator"
            )
            await db.messages.insert_one(ai_msg.model_dump())
            
            yield f"data: {json.dumps({'done': True, 'message_id': ai_msg.id})}\n\n"
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

# ============== AGENT STATUS ==============

@api_router.get("/projects/{project_id}/agents", response_model=List[AgentStatus])
async def get_agent_statuses(project_id: str):
    agents = await db.agent_status.find(
        {"project_id": project_id},
        {"_id": 0}
    ).to_list(20)
    
    # If no agents exist, create default ones
    if not agents:
        default_agents = [
            {"agent_type": "orchestrator", "status": "idle"},
            {"agent_type": "planner", "status": "idle"},
            {"agent_type": "coder", "status": "idle"},
            {"agent_type": "reviewer", "status": "idle"},
            {"agent_type": "tester", "status": "idle"},
            {"agent_type": "debugger", "status": "idle"},
            {"agent_type": "git", "status": "idle"},
        ]
        for agent_data in default_agents:
            agent = AgentStatus(project_id=project_id, **agent_data)
            await db.agent_status.insert_one(agent.model_dump())
            agents.append(agent.model_dump())
    
    return agents

@api_router.put("/projects/{project_id}/agents/{agent_type}")
async def update_agent_status(project_id: str, agent_type: str, status: str, message: Optional[str] = None):
    update_data = {
        "status": status,
        "message": message
    }
    
    if status == "running":
        update_data["started_at"] = datetime.now(timezone.utc).isoformat()
    elif status in ["completed", "error"]:
        update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.agent_status.update_one(
        {"project_id": project_id, "agent_type": agent_type},
        {"$set": update_data}
    )
    
    return {"updated": result.modified_count > 0}

# ============== GITHUB OPERATIONS ==============

@api_router.post("/github/import")
async def import_from_github(data: GitHubImport):
    """Clone a GitHub repository"""
    try:
        # Create project
        project_name = data.project_name or data.repo_url.split('/')[-1].replace('.git', '')
        project_obj = Project(
            name=project_name,
            description=f"Imported from {data.repo_url}",
            github_url=data.repo_url,
            project_type="fullstack"
        )
        
        workspace_path = WORKSPACES_DIR / project_obj.id
        
        # Clone repo
        clone_url = data.repo_url
        if github_token and 'github.com' in clone_url:
            # Add token for private repos
            clone_url = clone_url.replace('https://', f'https://{github_token}@')
        
        git.Repo.clone_from(clone_url, workspace_path, branch=data.branch)
        
        project_obj.workspace_path = str(workspace_path)
        await db.projects.insert_one(project_obj.model_dump())
        
        # Add log entry
        log = LogEntry(
            project_id=project_obj.id,
            level="success",
            message=f"Repository erfolgreich geklont: {data.repo_url}",
            source="git"
        )
        await db.logs.insert_one(log.model_dump())
        
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
        
        repo = git.Repo(workspace_path)
        
        # Stage all changes
        repo.git.add(A=True)
        
        # Commit
        repo.index.commit(data.message)
        
        # Push
        origin = repo.remote(name='origin')
        origin.push(data.branch)
        
        # Add log entry
        log = LogEntry(
            project_id=data.project_id,
            level="success",
            message=f"Änderungen committed und gepusht: {data.message}",
            source="git"
        )
        await db.logs.insert_one(log.model_dump())
        
        return {"success": True, "message": "Changes committed and pushed"}
        
    except Exception as e:
        logger.error(f"GitHub commit error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/github/branches/{project_id}")
async def get_branches(project_id: str):
    """Get available branches"""
    try:
        project = await db.projects.find_one({"id": project_id})
        if not project or not project.get('workspace_path'):
            raise HTTPException(status_code=404, detail="Project or workspace not found")
        
        repo = git.Repo(project['workspace_path'])
        branches = [ref.name for ref in repo.references if 'HEAD' not in ref.name]
        
        return {"branches": branches, "current": repo.active_branch.name}
        
    except Exception as e:
        logger.error(f"Get branches error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ============== ROADMAP ==============

@api_router.get("/projects/{project_id}/roadmap", response_model=List[RoadmapItem])
async def get_roadmap(project_id: str):
    items = await db.roadmap.find(
        {"project_id": project_id},
        {"_id": 0}
    ).sort("order", 1).to_list(100)
    return items

@api_router.post("/projects/{project_id}/roadmap", response_model=RoadmapItem)
async def add_roadmap_item(project_id: str, title: str, description: str):
    # Get current max order
    last_item = await db.roadmap.find_one(
        {"project_id": project_id},
        sort=[("order", -1)]
    )
    next_order = (last_item.get("order", 0) + 1) if last_item else 0
    
    item = RoadmapItem(
        project_id=project_id,
        title=title,
        description=description,
        order=next_order
    )
    await db.roadmap.insert_one(item.model_dump())
    return item

# ============== LOGS ==============

@api_router.get("/projects/{project_id}/logs", response_model=List[LogEntry])
async def get_logs(project_id: str, limit: int = 100):
    logs = await db.logs.find(
        {"project_id": project_id},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(limit)
    return logs

@api_router.post("/projects/{project_id}/logs", response_model=LogEntry)
async def add_log(project_id: str, level: str, message: str, source: str = "system"):
    log = LogEntry(
        project_id=project_id,
        level=level,
        message=message,
        source=source
    )
    await db.logs.insert_one(log.model_dump())
    return log

# ============== WORKSPACE FILES ==============

@api_router.get("/projects/{project_id}/files")
async def get_workspace_files(project_id: str, path: str = ""):
    """Get files in workspace directory"""
    project = await db.projects.find_one({"id": project_id})
    if not project or not project.get('workspace_path'):
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    workspace = Path(project['workspace_path'])
    target_path = workspace / path if path else workspace
    
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    
    if target_path.is_file():
        # Return file content
        async with aiofiles.open(target_path, 'r', errors='replace') as f:
            content = await f.read()
        return {"type": "file", "content": content, "path": str(path)}
    
    # Return directory listing
    items = []
    for item in target_path.iterdir():
        if item.name.startswith('.'):
            continue
        items.append({
            "name": item.name,
            "type": "directory" if item.is_dir() else "file",
            "path": str(item.relative_to(workspace))
        })
    
    return {"type": "directory", "items": sorted(items, key=lambda x: (x["type"] != "directory", x["name"]))}

@api_router.put("/projects/{project_id}/files")
async def save_workspace_file(project_id: str, path: str, content: str):
    """Save file in workspace"""
    project = await db.projects.find_one({"id": project_id})
    if not project or not project.get('workspace_path'):
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    workspace = Path(project['workspace_path'])
    target_path = workspace / path
    
    # Ensure parent directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiofiles.open(target_path, 'w') as f:
        await f.write(content)
    
    return {"success": True, "path": path}

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
