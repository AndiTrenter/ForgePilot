"""
Tool Registry System
Zentrales Tool-Management mit Permissions
"""
from typing import Dict, Callable, List, Optional, Any
from pydantic import BaseModel
from enum import Enum

class ToolPermission(str, Enum):
    """Tool-Berechtigungen"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ADMIN = "admin"

class ToolDefinition(BaseModel):
    """Tool-Definition"""
    name: str
    description: str
    parameters: Dict[str, Any]
    required_permissions: List[ToolPermission]
    handler: Optional[Callable] = None
    
    class Config:
        arbitrary_types_allowed = True

class ToolRegistry:
    """Zentrale Tool-Registry"""
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
    
    def register(self, tool: ToolDefinition):
        """Registriert ein Tool"""
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[ToolDefinition]:
        """Holt Tool-Definition"""
        return self._tools.get(name)
    
    def list_all(self) -> List[ToolDefinition]:
        """Listet alle Tools"""
        return list(self._tools.values())
    
    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        agent_permissions: List[ToolPermission]
    ) -> Dict[str, Any]:
        """Führt Tool aus (mit Permission-Check)"""
        tool = self.get(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found")
        
        # Permission-Check
        for perm in tool.required_permissions:
            if perm not in agent_permissions:
                raise PermissionError(
                    f"Agent lacks permission {perm} for tool {tool_name}"
                )
        
        # Execute
        if tool.handler:
            return await tool.handler(arguments)
        
        return {"error": "Tool handler not implemented"}

_registry: Optional[ToolRegistry] = None

def get_tool_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
