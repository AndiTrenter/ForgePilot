"""
Completion Gates System
Erzwingt Quality-Checks vor Task-Completion
"""
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel
import logging

from core.exceptions import GateViolationError
from core.database import get_database
from models.task import Task, TaskStatus

logger = logging.getLogger(__name__)


class GateCheck(BaseModel):
    """Einzelner Gate-Check"""
    name: str
    passed: bool
    message: str
    evidence: Optional[Dict[str, Any]] = None


class CompletionGate:
    """
    Completion Gate für Tasks
    Prüft ob Task als fertig markiert werden darf
    """
    
    def __init__(self, task: Task):
        self.task = task
        self.checks: List[GateCheck] = []
        self.db = get_database()
    
    async def can_complete(self) -> Tuple[bool, List[str]]:
        """
        Prüft alle Gates
        Returns: (can_complete, failed_checks)
        """
        self.checks = []
        failed = []
        
        # Gate 1: Build erfolgreich (nur für Code-Tasks)
        if self._requires_build():
            build_passed, build_msg = await self._check_build()
            self.checks.append(GateCheck(
                name="build",
                passed=build_passed,
                message=build_msg
            ))
            if not build_passed:
                failed.append("Build failed or missing")
        
        # Gate 2: Tests erfolgreich
        tests_passed, tests_msg = await self._check_tests()
        self.checks.append(GateCheck(
            name="tests",
            passed=tests_passed,
            message=tests_msg
        ))
        if not tests_passed:
            failed.append("Tests failed or missing")
        
        # Gate 3: Lint erfolgreich (nur für Code-Tasks)
        if self._requires_lint():
            lint_passed, lint_msg = await self._check_lint()
            self.checks.append(GateCheck(
                name="lint",
                passed=lint_passed,
                message=lint_msg
            ))
            if not lint_passed:
                failed.append("Lint failed")
        
        # Gate 4: Akzeptanzkriterien erfüllt
        criteria_passed, criteria_msg = await self._check_acceptance_criteria()
        self.checks.append(GateCheck(
            name="acceptance_criteria",
            passed=criteria_passed,
            message=criteria_msg
        ))
        if not criteria_passed:
            failed.append("Acceptance criteria not met")
        
        # Gate 5: Evidence vorhanden
        evidence_passed, evidence_msg = await self._check_evidence()
        self.checks.append(GateCheck(
            name="evidence",
            passed=evidence_passed,
            message=evidence_msg
        ))
        if not evidence_passed:
            failed.append("Evidence missing")
        
        # Gate 6: Code-Änderungen committed (bei Code-Tasks)
        if self._requires_commit():
            commit_passed, commit_msg = await self._check_commit()
            self.checks.append(GateCheck(
                name="commit",
                passed=commit_passed,
                message=commit_msg
            ))
            if not commit_passed:
                failed.append("Changes not committed")
        
        return (len(failed) == 0, failed)
    
    def _requires_build(self) -> bool:
        """Prüft ob Task Build erfordert"""
        return self.task.type in [
            "implementation",
            "refactoring",
            "debugging"
        ]
    
    def _requires_lint(self) -> bool:
        """Prüft ob Task Linting erfordert"""
        return self.task.type in [
            "implementation",
            "refactoring",
            "review"
        ]
    
    def _requires_commit(self) -> bool:
        """Prüft ob Task Commit erfordert"""
        return self.task.type in [
            "implementation",
            "refactoring",
            "debugging"
        ]
    
    async def _check_build(self) -> Tuple[bool, str]:
        """Prüft Build-Status"""
        try:
            # Hole Evidence aus DB
            evidence = await self.db.evidence.find_one({
                "task_id": self.task.id,
                "type": "build"
            })
            
            if not evidence:
                return (False, "No build evidence found")
            
            # Prüfe ob Build erfolgreich war
            if evidence.get("status") == "success":
                return (True, f"Build successful ({evidence.get('timestamp')})")
            else:
                return (False, f"Build failed: {evidence.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Build check error: {e}")
            return (False, f"Build check failed: {str(e)}")
    
    async def _check_tests(self) -> Tuple[bool, str]:
        """Prüft Test-Status"""
        try:
            # Hole Test-Evidence
            evidence = await self.db.evidence.find_one({
                "task_id": self.task.id,
                "type": "test"
            })
            
            if not evidence:
                # Für manche Tasks sind Tests optional
                if self.task.type in ["documentation", "research", "design"]:
                    return (True, "Tests not required for this task type")
                return (False, "No test evidence found")
            
            # Prüfe Test-Ergebnisse
            metadata = evidence.get("metadata", {})
            total = metadata.get("total", 0)
            passed = metadata.get("passed", 0)
            failed = metadata.get("failed", 0)
            
            if total == 0:
                return (False, "No tests executed")
            
            if failed > 0:
                return (False, f"{failed}/{total} tests failed")
            
            return (True, f"All {passed} tests passed")
            
        except Exception as e:
            logger.error(f"Test check error: {e}")
            return (False, f"Test check failed: {str(e)}")
    
    async def _check_lint(self) -> Tuple[bool, str]:
        """Prüft Lint-Status"""
        try:
            evidence = await self.db.evidence.find_one({
                "task_id": self.task.id,
                "type": "lint"
            })
            
            if not evidence:
                return (False, "No lint evidence found")
            
            if evidence.get("status") == "success":
                return (True, "Lint passed")
            else:
                return (False, f"Lint failed: {evidence.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Lint check error: {e}")
            return (False, f"Lint check failed: {str(e)}")
    
    async def _check_acceptance_criteria(self) -> Tuple[bool, str]:
        """Prüft Akzeptanzkriterien"""
        criteria = self.task.acceptance_criteria
        
        if not criteria:
            return (True, "No acceptance criteria defined")
        
        total = len(criteria)
        met = sum(1 for c in criteria if c.met)
        
        if met < total:
            unmet = [c.description for c in criteria if not c.met]
            return (False, f"{total - met}/{total} criteria not met: {', '.join(unmet[:3])}")
        
        return (True, f"All {total} acceptance criteria met")
    
    async def _check_evidence(self) -> Tuple[bool, str]:
        """Prüft ob Evidence vorhanden"""
        try:
            count = await self.db.evidence.count_documents({
                "task_id": self.task.id
            })
            
            if count == 0:
                return (False, "No evidence collected")
            
            return (True, f"{count} evidence artifacts collected")
            
        except Exception as e:
            logger.error(f"Evidence check error: {e}")
            return (False, f"Evidence check failed: {str(e)}")
    
    async def _check_commit(self) -> Tuple[bool, str]:
        """Prüft ob Änderungen committed wurden"""
        try:
            # Hole Commit-Evidence
            evidence = await self.db.evidence.find_one({
                "task_id": self.task.id,
                "type": "commit"
            })
            
            if not evidence:
                return (False, "Changes not committed")
            
            commit_hash = evidence.get("metadata", {}).get("commit_hash")
            if commit_hash:
                return (True, f"Changes committed: {commit_hash[:8]}")
            else:
                return (False, "Commit hash missing")
                
        except Exception as e:
            logger.error(f"Commit check error: {e}")
            return (False, f"Commit check failed: {str(e)}")
    
    async def get_report(self) -> Dict[str, Any]:
        """Erstellt Gate-Report"""
        can_complete, failed = await self.can_complete()
        
        return {
            "task_id": self.task.id,
            "can_complete": can_complete,
            "failed_checks": failed,
            "checks": [
                {
                    "name": check.name,
                    "passed": check.passed,
                    "message": check.message
                }
                for check in self.checks
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def enforce_completion_gate(task: Task) -> Dict[str, Any]:
    """
    Erzwingt Completion-Gate für Task
    Raises GateViolationError wenn Gates nicht erfüllt
    """
    gate = CompletionGate(task)
    can_complete, failed = await gate.can_complete()
    
    if not can_complete:
        report = await gate.get_report()
        raise GateViolationError(
            f"Cannot complete task '{task.name}'. Failed checks: {', '.join(failed)}",
            failed_checks=failed
        )
    
    # Speichere Gate-Report
    report = await gate.get_report()
    db = get_database()
    await db.evidence.insert_one({
        "task_id": task.id,
        "type": "gate_report",
        "status": "passed",
        "content": report,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return report
