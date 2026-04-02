"""
Model Router
Intelligentes Routing zu optimalen Models
"""
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel

class TaskType(str, Enum):
    ORCHESTRATION = "orchestration"
    CODE_GENERATION = "code_generation"
    REVIEW = "review"
    TESTING = "testing"
    SIMPLE_COMPLETION = "simple_completion"
    LONG_CONTEXT = "long_context"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ModelSelection(BaseModel):
    provider: str
    model: str
    reason: str
    estimated_cost: float

class ModelRouter:
    """Model-Routing Engine"""
    
    def __init__(self, config: dict):
        self.config = config
    
    async def route_request(
        self,
        task_type: TaskType,
        context_size: int = 0,
        priority: Priority = Priority.MEDIUM,
        budget_constraint: Optional[float] = None
    ) -> ModelSelection:
        """Wählt optimales Model"""
        
        # Orchestration → Starkes Model
        if task_type == TaskType.ORCHESTRATION:
            return ModelSelection(
                provider="openai",
                model="gpt-4o",
                reason="Orchestration requires strong reasoning",
                estimated_cost=0.025
            )
        
        # Long Context → Spezialisiertes Model
        if context_size > 100000 or task_type == TaskType.LONG_CONTEXT:
            return ModelSelection(
                provider="anthropic",
                model="claude-sonnet-4",
                reason="Large context requires long-context model",
                estimated_cost=0.030
            )
        
        # High Priority → Bestes Model
        if priority in [Priority.HIGH, Priority.CRITICAL]:
            return ModelSelection(
                provider="openai",
                model="gpt-4o",
                reason="High priority requires best model",
                estimated_cost=0.025
            )
        
        # Budget-optimiert → Günstiges Model
        if budget_constraint and budget_constraint < 0.01:
            return ModelSelection(
                provider="openai",
                model="gpt-4o-mini",
                reason="Budget constraint requires cost-effective model",
                estimated_cost=0.002
            )
        
        # Default: Balanced
        return ModelSelection(
            provider="openai",
            model="gpt-4o-mini",
            reason="Balanced performance/cost",
            estimated_cost=0.002
        )

_router: Optional[ModelRouter] = None

def get_model_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter(config={})
    return _router
