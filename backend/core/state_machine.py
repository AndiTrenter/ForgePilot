"""
State Machine für Projekt- und Task-Zustände
Erzwingt valide Zustandsübergänge
"""
from enum import Enum
from typing import Optional, Set
from datetime import datetime, timezone

from core.exceptions import StateTransitionError


class ProjectStatus(str, Enum):
    """Projekt-Zustände"""
    DISCOVERY = "discovery"
    AWAITING_USER = "awaiting_user"
    SOLUTION_DESIGN = "solution_design"
    PLANNING = "planning"
    PROVISIONING = "provisioning"
    IMPLEMENTING = "implementing"
    REVIEWING = "reviewing"
    TESTING = "testing"
    DEBUGGING = "debugging"
    READY_FOR_HANDOVER = "ready_for_handover"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class TaskStatus(str, Enum):
    """Task-Zustände"""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    UNDER_REVIEW = "under_review"
    UNDER_TEST = "under_test"
    FAILED = "failed"
    PASSED = "passed"
    DONE = "done"


# Erlaubte Zustandsübergänge
PROJECT_TRANSITIONS: dict[ProjectStatus, Set[ProjectStatus]] = {
    ProjectStatus.DISCOVERY: {
        ProjectStatus.AWAITING_USER,
        ProjectStatus.SOLUTION_DESIGN,
        ProjectStatus.FAILED
    },
    ProjectStatus.AWAITING_USER: {
        ProjectStatus.DISCOVERY,
        ProjectStatus.SOLUTION_DESIGN,
        ProjectStatus.PAUSED
    },
    ProjectStatus.SOLUTION_DESIGN: {
        ProjectStatus.PLANNING,
        ProjectStatus.AWAITING_USER,
        ProjectStatus.FAILED
    },
    ProjectStatus.PLANNING: {
        ProjectStatus.PROVISIONING,
        ProjectStatus.AWAITING_USER,
        ProjectStatus.FAILED
    },
    ProjectStatus.PROVISIONING: {
        ProjectStatus.IMPLEMENTING,
        ProjectStatus.FAILED
    },
    ProjectStatus.IMPLEMENTING: {
        ProjectStatus.REVIEWING,
        ProjectStatus.TESTING,
        ProjectStatus.DEBUGGING,
        ProjectStatus.PAUSED,
        ProjectStatus.FAILED
    },
    ProjectStatus.REVIEWING: {
        ProjectStatus.IMPLEMENTING,
        ProjectStatus.TESTING,
        ProjectStatus.FAILED
    },
    ProjectStatus.TESTING: {
        ProjectStatus.DEBUGGING,
        ProjectStatus.READY_FOR_HANDOVER,
        ProjectStatus.IMPLEMENTING,
        ProjectStatus.FAILED
    },
    ProjectStatus.DEBUGGING: {
        ProjectStatus.IMPLEMENTING,
        ProjectStatus.TESTING,
        ProjectStatus.FAILED
    },
    ProjectStatus.READY_FOR_HANDOVER: {
        ProjectStatus.COMPLETED,
        ProjectStatus.IMPLEMENTING  # Für Last-Minute-Änderungen
    },
    ProjectStatus.COMPLETED: set(),  # Terminal State
    ProjectStatus.FAILED: {
        ProjectStatus.DISCOVERY  # Neustart möglich
    },
    ProjectStatus.PAUSED: {
        ProjectStatus.IMPLEMENTING,
        ProjectStatus.AWAITING_USER
    }
}

TASK_TRANSITIONS: dict[TaskStatus, Set[TaskStatus]] = {
    TaskStatus.QUEUED: {
        TaskStatus.IN_PROGRESS,
        TaskStatus.BLOCKED
    },
    TaskStatus.IN_PROGRESS: {
        TaskStatus.UNDER_REVIEW,
        TaskStatus.UNDER_TEST,
        TaskStatus.BLOCKED,
        TaskStatus.FAILED
    },
    TaskStatus.BLOCKED: {
        TaskStatus.QUEUED,
        TaskStatus.IN_PROGRESS
    },
    TaskStatus.UNDER_REVIEW: {
        TaskStatus.IN_PROGRESS,
        TaskStatus.UNDER_TEST,
        TaskStatus.PASSED,
        TaskStatus.FAILED
    },
    TaskStatus.UNDER_TEST: {
        TaskStatus.IN_PROGRESS,
        TaskStatus.FAILED,
        TaskStatus.PASSED
    },
    TaskStatus.FAILED: {
        TaskStatus.QUEUED,
        TaskStatus.IN_PROGRESS
    },
    TaskStatus.PASSED: {
        TaskStatus.DONE
    },
    TaskStatus.DONE: set()  # Terminal State
}


class StateMachine:
    """Zustandsmaschine für sichere State-Transitions"""
    
    @staticmethod
    def can_transition_project(
        current: ProjectStatus,
        target: ProjectStatus
    ) -> bool:
        """Prüft ob Projekt-Statuswechsel erlaubt ist"""
        return target in PROJECT_TRANSITIONS.get(current, set())
    
    @staticmethod
    def can_transition_task(
        current: TaskStatus,
        target: TaskStatus
    ) -> bool:
        """Prüft ob Task-Statuswechsel erlaubt ist"""
        return target in TASK_TRANSITIONS.get(current, set())
    
    @staticmethod
    async def transition_project(
        project_id: str,
        current: ProjectStatus,
        target: ProjectStatus,
        reason: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Führt Projekt-Statuswechsel durch
        Raises StateTransitionError wenn nicht erlaubt
        """
        if not StateMachine.can_transition_project(current, target):
            raise StateTransitionError(
                f"Invalid project transition: {current.value} → {target.value}",
                {
                    "project_id": project_id,
                    "current": current.value,
                    "target": target.value,
                    "allowed": [s.value for s in PROJECT_TRANSITIONS.get(current, set())]
                }
            )
        
        transition_log = {
            "project_id": project_id,
            "from_status": current.value,
            "to_status": target.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "metadata": metadata or {}
        }
        
        # TODO: In database speichern
        
        return transition_log
    
    @staticmethod
    async def transition_task(
        task_id: str,
        current: TaskStatus,
        target: TaskStatus,
        reason: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Führt Task-Statuswechsel durch
        Raises StateTransitionError wenn nicht erlaubt
        """
        if not StateMachine.can_transition_task(current, target):
            raise StateTransitionError(
                f"Invalid task transition: {current.value} → {target.value}",
                {
                    "task_id": task_id,
                    "current": current.value,
                    "target": target.value,
                    "allowed": [s.value for s in TASK_TRANSITIONS.get(current, set())]
                }
            )
        
        transition_log = {
            "task_id": task_id,
            "from_status": current.value,
            "to_status": target.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "metadata": metadata or {}
        }
        
        # TODO: In database speichern
        
        return transition_log
    
    @staticmethod
    def get_allowed_project_transitions(current: ProjectStatus) -> list[ProjectStatus]:
        """Gibt erlaubte Projekt-Übergänge zurück"""
        return list(PROJECT_TRANSITIONS.get(current, set()))
    
    @staticmethod
    def get_allowed_task_transitions(current: TaskStatus) -> list[TaskStatus]:
        """Gibt erlaubte Task-Übergänge zurück"""
        return list(TASK_TRANSITIONS.get(current, set()))
