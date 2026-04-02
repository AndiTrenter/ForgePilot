"""
Discovery Service
Analysiert Anforderungen und extrahiert Scope
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class DiscoveryBrief(BaseModel):
    user_request: str
    scope: Dict[str, Any]
    assumptions: List[str]
    critical_questions: List[str]
    risk_factors: List[str]

class DiscoveryService:
    """Discovery Phase Service"""
    
    async def analyze_request(self, user_request: str) -> DiscoveryBrief:
        """Analysiert User-Request"""
        
        # Scope-Extraktion (vereinfacht)
        scope = {
            "type": self._detect_project_type(user_request),
            "complexity": self._estimate_complexity(user_request),
            "features": self._extract_features(user_request)
        }
        
        # Annahmen
        assumptions = [
            "Browser-Kompatibilität: Moderne Browser (Chrome, Firefox, Safari)",
            "Performance-Ziel: <100ms Response-Zeit",
            "Deployment: Docker-Container"
        ]
        
        # Kritische Fragen
        questions = []
        if "datenbank" in user_request.lower():
            questions.append("Welche Art von Daten sollen gespeichert werden?")
        
        if "benutzer" in user_request.lower() or "user" in user_request.lower():
            questions.append("Soll es eine Benutzer-Authentifizierung geben?")
        
        # Risiken
        risks = []
        if scope["complexity"] == "high":
            risks.append("Hohe Komplexität könnte Entwicklungszeit verlängern")
        
        return DiscoveryBrief(
            user_request=user_request,
            scope=scope,
            assumptions=assumptions,
            critical_questions=questions,
            risk_factors=risks
        )
    
    def _detect_project_type(self, request: str) -> str:
        req_lower = request.lower()
        if "spiel" in req_lower or "game" in req_lower:
            return "browser_game"
        if "dashboard" in req_lower:
            return "dashboard"
        if "api" in req_lower:
            return "api"
        return "fullstack"
    
    def _estimate_complexity(self, request: str) -> str:
        word_count = len(request.split())
        if word_count < 10:
            return "low"
        if word_count < 30:
            return "medium"
        return "high"
    
    def _extract_features(self, request: str) -> List[str]:
        features = []
        req_lower = request.lower()
        
        if "user" in req_lower or "benutzer" in req_lower:
            features.append("user_management")
        if "datenbank" in req_lower or "database" in req_lower:
            features.append("data_persistence")
        if "api" in req_lower:
            features.append("rest_api")
        
        return features

_service: Optional[DiscoveryService] = None

def get_discovery_service() -> DiscoveryService:
    global _service
    if _service is None:
        _service = DiscoveryService()
    return _service
