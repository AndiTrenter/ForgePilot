"""
Pydantic Models für Projekte
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum

from core.state_machine import ProjectStatus


class ProjectType(str, Enum):
    """Projekt-Typen"""
    FULLSTACK = "fullstack"
    FRONTEND = "frontend"
    BACKEND = "backend"
    API = "api"
    BROWSER_GAME = "browser_game"
    DASHBOARD = "dashboard"
    SAAS = "saas"
    CRUD_APP = "crud_app"
    LANDING_PAGE = "landing_page"
    ADMIN_PANEL = "admin_panel"
    CLI_TOOL = "cli_tool"
    OTHER = "other"


class TechStack(BaseModel):
    """Tech Stack Definition"""
    frontend: Optional[str] = None
    backend: Optional[str] = None
    database: Optional[str] = None
    language: Optional[str] = None
    framework: Optional[str] = None
    testing: Optional[str] = None
    build: Optional[str] = None


class ProjectMetadata(BaseModel):
    """Projekt-Metadaten"""
    user_request: str
    assumptions: List[str] = Field(default_factory=list)
    scope: Optional[dict] = None
    architecture: Optional[dict] = None
    risks: List[str] = Field(default_factory=list)
    tech_stack: Optional[TechStack] = None


class Project(BaseModel):
    """Projekt-Model"""
    id: str
    name: str
    description: str
    project_type: ProjectType
    status: ProjectStatus = ProjectStatus.DISCOVERY
    
    # Metadata
    metadata: ProjectMetadata
    
    # Timestamps
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    
    # Archive
    archived: bool = False
    archived_at: Optional[str] = None
    
    # Settings
    github_repo: Optional[str] = None
    github_branch: Optional[str] = None
    
    # Workspace
    workspace_path: Optional[str] = None
    
    # Progress
    current_phase: Optional[str] = None
    completion_percentage: int = 0
    
    class Config:
        use_enum_values = True


class ProjectCreate(BaseModel):
    """Projekt erstellen Request"""
    name: str
    description: str
    project_type: ProjectType
    user_request: str
    github_repo: Optional[str] = None
    assumptions: List[str] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    """Projekt aktualisieren Request"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    metadata: Optional[dict] = None
    completion_percentage: Optional[int] = None
    current_phase: Optional[str] = None
