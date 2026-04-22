"""
ForgePilot Policy Engine

Kategorisiert Aktionen/Tools in drei Sicherheitsstufen:
- AUTO_ALLOWED: Der Agent darf diese Aktion autonom ausführen.
- APPROVAL_REQUIRED: Kritische Aktion, braucht explizite User-Freigabe.
- FORBIDDEN: Destruktive Aktion, wird IMMER blockiert.

Diese Engine ist die zentrale Schutzschicht vor dem Deploy-Orchestrator
und wird vor jedem kritischen Tool-Aufruf konsultiert.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Set


# Aktionen, die der Agent OHNE Rückfrage ausführen darf.
AUTO_ALLOWED: Set[str] = {
    # Dateisystem (Workspace)
    "read_file",
    "read_repo",
    "view_file",
    "list_files",
    "create_file",
    "edit_file",
    "delete_file",
    "search",
    "grep",
    # Build & Test (lokal / Staging)
    "install_package",
    "build_app",
    "run_tests",
    "lint",
    "type_check",
    "browser_test",
    "screenshot",
    "code_review",
    "verify_game",
    # Preview / Staging (nicht Production)
    "build_staging",
    "deploy_preview",
    "start_dev_server",
    "start_backend",
    "start_frontend",
    # Agent-interne Utilities
    "think",
    "clear_errors",
    "web_search",
    "run_command",  # Sandbox-Shell im Workspace
}

# Aktionen, die echten User-Impact haben: brauchen explizite Freigabe.
APPROVAL_REQUIRED: Set[str] = {
    "deploy_production",
    "db_migration",
    "docker_restart",
    "docker_compose_up",
    "docker_compose_down",
    "reverse_proxy_change",
    "nginx_reload",
    "service_installation",
    "network_change",
    "dns_change",
    "secret_rotation",
    "env_change_production",
    "publish_package",
    "push_main_branch",
    "create_release",
    "mark_complete",  # Abschluss-Signal = Freigabe-Gate
}

# Aktionen, die NIEMALS ausgeführt werden dürfen - auch nicht mit Approval.
FORBIDDEN: Set[str] = {
    "delete_volume",
    "wipe_database",
    "drop_database",
    "disable_firewall",
    "rm_rf_root",
    "force_push_main",
    "delete_git_history",
    "delete_backup",
}


@dataclass
class PolicyDecision:
    action: str
    allowed: bool
    requires_approval: bool
    reason: str
    category: str  # 'auto' | 'approval' | 'forbidden' | 'unknown'

    def to_dict(self) -> Dict:
        return {
            "action": self.action,
            "allowed": self.allowed,
            "requires_approval": self.requires_approval,
            "reason": self.reason,
            "category": self.category,
        }


def evaluate_action(action_name: str) -> PolicyDecision:
    """Entscheidet, ob eine Aktion zulässig ist.

    Args:
        action_name: Name des Tools bzw. der Aktion (z. B. 'deploy_production').

    Returns:
        PolicyDecision mit Feldern allowed / requires_approval / reason / category.

    Semantik:
        - FORBIDDEN  -> allowed=False, requires_approval=False
        - AUTO       -> allowed=True,  requires_approval=False
        - APPROVAL   -> allowed=True,  requires_approval=True  (erst nach set_approval ausführen)
        - UNKNOWN    -> allowed=False, requires_approval=True  (fail-closed: lieber fragen)
    """
    if not isinstance(action_name, str) or not action_name.strip():
        return PolicyDecision(
            action=str(action_name),
            allowed=False,
            requires_approval=False,
            reason="Leerer oder ungültiger Action-Name.",
            category="forbidden",
        )

    name = action_name.strip()

    if name in FORBIDDEN:
        return PolicyDecision(
            action=name,
            allowed=False,
            requires_approval=False,
            reason=f"Aktion '{name}' ist destruktiv und dauerhaft blockiert.",
            category="forbidden",
        )

    if name in APPROVAL_REQUIRED:
        return PolicyDecision(
            action=name,
            allowed=True,
            requires_approval=True,
            reason=f"Aktion '{name}' hat Produktions-Impact und braucht User-Freigabe.",
            category="approval",
        )

    if name in AUTO_ALLOWED:
        return PolicyDecision(
            action=name,
            allowed=True,
            requires_approval=False,
            reason=f"Aktion '{name}' ist im sicheren Autonomie-Bereich.",
            category="auto",
        )

    # Fail-closed: unbekannte Aktionen werden sicherheitshalber als Approval-pflichtig eingestuft.
    return PolicyDecision(
        action=name,
        allowed=True,
        requires_approval=True,
        reason=f"Aktion '{name}' ist unbekannt - Fail-closed: Freigabe angefordert.",
        category="unknown",
    )


def is_forbidden(action_name: str) -> bool:
    return evaluate_action(action_name).category == "forbidden"


def needs_approval(action_name: str) -> bool:
    d = evaluate_action(action_name)
    return d.requires_approval and d.allowed


def is_auto_allowed(action_name: str) -> bool:
    return evaluate_action(action_name).category == "auto"


__all__ = [
    "AUTO_ALLOWED",
    "APPROVAL_REQUIRED",
    "FORBIDDEN",
    "PolicyDecision",
    "evaluate_action",
    "is_forbidden",
    "needs_approval",
    "is_auto_allowed",
]
