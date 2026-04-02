"""
Pydantic Models für Tasks
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from core.state_machine import TaskStatus


class TaskType(str, Enum):
    """Task-Typen"""
    DISCOVERY = "discovery"
    RESEARCH = "research"
    DESIGN = "design"
    PLANNING = "planning"
    PROVISIONING = "provisioning"
    IMPLEMENTATION = "implementation"
    REFACTORING = "refactoring"
    REVIEW = "review"
    TESTING = "testing"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"
    DEPLOYMENT = "deployment"


class TaskPriority(str, Enum):
    """Task-Prioritäten"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AcceptanceCriteria(BaseModel):
    """Akzeptanzkriterium"""
    id: str
    description: str
    met: bool = False
    evidence: Optional[str] = None


class Task(BaseModel):
    """Task-Model"""
    id: str
    project_id: str
    name: str
    description: str
    type: TaskType
    status: TaskStatus = TaskStatus.QUEUED
    priority: TaskPriority = TaskPriority.MEDIUM
    
    # Acceptance Criteria
    acceptance_criteria: List[AcceptanceCriteria] = Field(default_factory=list)
    
    # Dependencies
    depends_on: List[str] = Field(default_factory=list)
    blocked_by: List[str] = Field(default_factory=list)
    
    # Assignment
    assigned_agent: Optional[str] = None
    
    # Timestamps
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Estimation
    estimated_effort: Optional[int] = None  # in minutes
    actual_effort: Optional[int] = None
    
    # Evidence
    evidence_id: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class TaskCreate(BaseModel):
    """Task erstellen Request"""
    project_id: str
    name: str
    description: str
    type: TaskType
    priority: TaskPriority = TaskPriority.MEDIUM
    acceptance_criteria: List[str] = Field(default_factory=list)
    depends_on: List[str] = Field(default_factory=list)
    assigned_agent: Optional[str] = None
    estimated_effort: Optional[int] = None


class TaskUpdate(BaseModel):
    """Task aktualisieren Request"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assigned_agent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
