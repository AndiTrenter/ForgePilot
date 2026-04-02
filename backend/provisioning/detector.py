"""
Tech Stack Detection
Erkennt automatisch passenden Tech-Stack
"""
from typing import Dict, Optional
from pydantic import BaseModel

class TechStack(BaseModel):
    frontend: Optional[str] = None
    backend: Optional[str] = None
    database: Optional[str] = None
    language: str = "javascript"
    framework: Optional[str] = None
    build_tool: Optional[str] = None
    test_framework: Optional[str] = None

async def detect_stack_from_requirements(requirements: str) -> TechStack:
    """Erkennt Tech-Stack aus Anforderungen"""
    
    req_lower = requirements.lower()
    
    # Browser-Game
    if any(word in req_lower for word in ['spiel', 'game', 'browser', 'spielbar']):
        return TechStack(
            frontend="vite + react",
            backend=None,
            database=None,
            language="typescript",
            framework="react",
            build_tool="vite",
            test_framework="vitest"
        )
    
    # Dashboard / CRUD
    if any(word in req_lower for word in ['dashboard', 'crud', 'verwaltung', 'admin']):
        return TechStack(
            frontend="next.js",
            backend="fastapi",
            database="postgresql",
            language="typescript",
            framework="next.js",
            build_tool="next",
            test_framework="jest"
        )
    
    # API
    if any(word in req_lower for word in ['api', 'backend', 'rest', 'graphql']):
        return TechStack(
            frontend=None,
            backend="fastapi",
            database="postgresql",
            language="python",
            framework="fastapi",
            build_tool=None,
            test_framework="pytest"
        )
    
    # Default: Fullstack
    return TechStack(
        frontend="vite + react",
        backend="fastapi",
        database="sqlite",
        language="typescript",
        framework="react",
        build_tool="vite",
        test_framework="vitest"
    )
