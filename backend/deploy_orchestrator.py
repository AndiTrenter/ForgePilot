"""
ForgePilot Delivery Orchestrator

Zustandsmaschine für den Delivery-Prozess pro Projekt/Session:

    REQUIREMENTS -> PLAN -> BUILD -> VERIFY
                                -> PREVIEW_READY -> AWAITING_APPROVAL
                                -> DEPLOYING -> DONE
    (BLOCKED ist Fehlerzustand, REJECTED wenn User ablehnt)

Daten werden in MongoDB-Collection 'delivery_jobs' persistiert.

Nutzung:
    from deploy_orchestrator import DeliveryOrchestrator, DeliveryStage
    orch = DeliveryOrchestrator(db)
    job_id = await orch.create_job(project_id, session_id, user_id, request_text)
    await orch.update_stage(job_id, DeliveryStage.BUILD)
    await orch.set_preview(job_id, "https://...", checks=["Login funktioniert", "Form speichert"])
    await orch.request_approval(job_id, summary="Feature fertig, bitte testen")
    await orch.set_approval(job_id, approved=True, approved_by="user:anditrenter")
    await orch.finalize_job(job_id, result={"deployed": True})
"""
from __future__ import annotations
import uuid
import logging
from enum import Enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("forgepilot.deploy_orchestrator")


class DeliveryStage(str, Enum):
    REQUIREMENTS = "requirements"
    PLAN = "plan"
    BUILD = "build"
    VERIFY = "verify"
    PREVIEW_READY = "preview_ready"
    AWAITING_APPROVAL = "awaiting_approval"
    DEPLOYING = "deploying"
    DONE = "done"
    BLOCKED = "blocked"
    REJECTED = "rejected"


# Erlaubte Transitionen. Wird validiert, um inkonsistente Zustände zu vermeiden.
_ALLOWED_TRANSITIONS: Dict[DeliveryStage, set] = {
    DeliveryStage.REQUIREMENTS: {DeliveryStage.PLAN, DeliveryStage.BLOCKED},
    DeliveryStage.PLAN: {DeliveryStage.BUILD, DeliveryStage.REQUIREMENTS, DeliveryStage.BLOCKED},
    DeliveryStage.BUILD: {DeliveryStage.VERIFY, DeliveryStage.BUILD, DeliveryStage.BLOCKED},
    DeliveryStage.VERIFY: {
        DeliveryStage.PREVIEW_READY,
        DeliveryStage.BUILD,  # Fix nach Testfehler
        DeliveryStage.BLOCKED,
    },
    DeliveryStage.PREVIEW_READY: {
        DeliveryStage.AWAITING_APPROVAL,
        DeliveryStage.BUILD,  # User verlangt Änderungen
        DeliveryStage.BLOCKED,
    },
    DeliveryStage.AWAITING_APPROVAL: {
        DeliveryStage.DEPLOYING,
        DeliveryStage.BUILD,  # Änderungswunsch
        DeliveryStage.REJECTED,
        DeliveryStage.BLOCKED,
    },
    DeliveryStage.DEPLOYING: {DeliveryStage.DONE, DeliveryStage.BLOCKED},
    DeliveryStage.DONE: set(),
    DeliveryStage.BLOCKED: {
        DeliveryStage.REQUIREMENTS,
        DeliveryStage.PLAN,
        DeliveryStage.BUILD,
        DeliveryStage.VERIFY,
    },
    DeliveryStage.REJECTED: {DeliveryStage.BUILD, DeliveryStage.REQUIREMENTS},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DeliveryOrchestrator:
    """Async Orchestrator für Delivery-Jobs auf Basis einer Motor-MongoDB."""

    def __init__(self, db, collection_name: str = "delivery_jobs"):
        self.db = db
        self.coll = db[collection_name]

    # ---------- Queries ----------
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return await self.coll.find_one({"job_id": job_id}, {"_id": 0})

    async def get_active_job(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Liefert den jüngsten nicht-terminalen Job eines Projekts."""
        terminal = [DeliveryStage.DONE.value, DeliveryStage.REJECTED.value]
        return await self.coll.find_one(
            {"project_id": project_id, "stage": {"$nin": terminal}},
            {"_id": 0},
            sort=[("created_at", -1)],
        )

    async def list_jobs(self, project_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        cursor = self.coll.find({"project_id": project_id}, {"_id": 0}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(limit)

    # ---------- Lifecycle ----------
    async def create_job(
        self,
        project_id: str,
        session_id: Optional[str],
        user_id: Optional[str],
        request_text: str,
    ) -> str:
        job_id = str(uuid.uuid4())
        now = _now_iso()
        doc = {
            "job_id": job_id,
            "project_id": project_id,
            "session_id": session_id,
            "user_id": user_id,
            "request_text": request_text,
            "stage": DeliveryStage.REQUIREMENTS.value,
            "preview_url": None,
            "preview_checks": [],
            "approval_required": False,
            "approved": False,
            "approved_by": None,
            "approved_at": None,
            "rejected_reason": None,
            "summary": None,
            "deploy_plan": None,
            "verification_report": None,
            "result": None,
            "stage_history": [{"stage": DeliveryStage.REQUIREMENTS.value, "at": now}],
            "logs": [{"at": now, "level": "info", "msg": "Job erstellt"}],
            "created_at": now,
            "updated_at": now,
        }
        await self.coll.insert_one(doc)
        logger.info("Delivery job created: %s for project %s", job_id, project_id)
        return job_id

    async def append_log(self, job_id: str, level: str, msg: str) -> None:
        entry = {"at": _now_iso(), "level": level, "msg": msg}
        await self.coll.update_one(
            {"job_id": job_id},
            {"$push": {"logs": entry}, "$set": {"updated_at": _now_iso()}},
        )

    async def update_stage(
        self,
        job_id: str,
        new_stage: DeliveryStage,
        meta: Optional[Dict[str, Any]] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Validiert Stage-Übergang und persistiert ihn.

        Args:
            force: Wenn True, wird die Transition auch bei nicht erlaubtem Pfad durchgeführt.
                   Sollte nur in Ausnahmen (z. B. Admin-Reset) verwendet werden.
        """
        if isinstance(new_stage, str):
            new_stage = DeliveryStage(new_stage)

        job = await self.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} nicht gefunden")

        current = DeliveryStage(job["stage"])
        allowed = _ALLOWED_TRANSITIONS.get(current, set())
        if not force and new_stage != current and new_stage not in allowed:
            raise ValueError(
                f"Ungültiger Übergang {current.value} -> {new_stage.value}. "
                f"Erlaubt: {[s.value for s in allowed]}"
            )

        now = _now_iso()
        update = {
            "stage": new_stage.value,
            "updated_at": now,
        }
        if meta:
            for k, v in meta.items():
                if k in {"job_id", "created_at", "stage_history", "logs"}:
                    continue
                update[k] = v

        history_entry = {"stage": new_stage.value, "at": now}
        if meta and "reason" in meta:
            history_entry["reason"] = meta["reason"]

        await self.coll.update_one(
            {"job_id": job_id},
            {
                "$set": update,
                "$push": {
                    "stage_history": history_entry,
                    "logs": {"at": now, "level": "info", "msg": f"Stage -> {new_stage.value}"},
                },
            },
        )
        return await self.get_job(job_id)

    async def set_preview(
        self,
        job_id: str,
        preview_url: str,
        checks: Optional[List[str]] = None,
        summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        meta = {
            "preview_url": preview_url,
            "preview_checks": checks or [],
        }
        if summary:
            meta["summary"] = summary
        return await self.update_stage(job_id, DeliveryStage.PREVIEW_READY, meta=meta)

    async def request_approval(
        self,
        job_id: str,
        summary: Optional[str] = None,
        deploy_plan: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        meta: Dict[str, Any] = {
            "approval_required": True,
        }
        if summary is not None:
            meta["summary"] = summary
        if deploy_plan is not None:
            meta["deploy_plan"] = deploy_plan
        return await self.update_stage(job_id, DeliveryStage.AWAITING_APPROVAL, meta=meta)

    async def set_approval(
        self,
        job_id: str,
        approved: bool,
        approved_by: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Markiert eine Freigabe (oder Ablehnung).

        Bei approved=True wird Stage -> DEPLOYING gesetzt.
        Bei approved=False wird Stage -> REJECTED gesetzt.
        """
        job = await self.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} nicht gefunden")
        if job["stage"] != DeliveryStage.AWAITING_APPROVAL.value:
            raise ValueError(
                f"Job ist in Stage '{job['stage']}' - Freigabe nur in '{DeliveryStage.AWAITING_APPROVAL.value}' möglich."
            )

        now = _now_iso()
        if approved:
            meta = {
                "approved": True,
                "approved_by": approved_by,
                "approved_at": now,
                "approval_required": False,
            }
            if reason:
                meta["reason"] = reason
            return await self.update_stage(job_id, DeliveryStage.DEPLOYING, meta=meta)
        else:
            meta = {
                "approved": False,
                "approved_by": approved_by,
                "approved_at": now,
                "rejected_reason": reason or "User lehnte Freigabe ab.",
                "approval_required": False,
            }
            return await self.update_stage(job_id, DeliveryStage.REJECTED, meta=meta)

    async def finalize_job(self, job_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Beendet den Job erfolgreich (Stage = DONE)."""
        return await self.update_stage(
            job_id,
            DeliveryStage.DONE,
            meta={"result": result},
        )

    async def block(self, job_id: str, reason: str) -> Dict[str, Any]:
        return await self.update_stage(
            job_id,
            DeliveryStage.BLOCKED,
            meta={"reason": reason, "rejected_reason": None},
            force=True,
        )

    # ---------- Helpers ----------
    @staticmethod
    def approval_keywords() -> List[str]:
        """Keywords im User-Chat, die eine Freigabe signalisieren."""
        return [
            "freigeben",
            "freigabe",
            "freigegeben",
            "genehmigt",
            "approve",
            "approved",
            "go live",
            "golive",
            "deploy",
            "deploye",
            "ausrollen",
            "ship it",
            "produktiv",
            "production",
        ]

    @staticmethod
    def rejection_keywords() -> List[str]:
        return [
            "nicht freigeben",
            "ablehnen",
            "reject",
            "stopp",
            "stop",
            "abbrechen",
            "noch nicht",
            "warte",
        ]

    @classmethod
    def detect_approval(cls, text: str) -> Optional[bool]:
        """Liefert True/False/None je nach Keyword im Usertext.

        True  -> Freigabe
        False -> Ablehnung
        None  -> kein Signal erkannt
        """
        if not text:
            return None
        low = text.strip().lower()
        for kw in cls.rejection_keywords():
            if kw in low:
                return False
        for kw in cls.approval_keywords():
            if kw in low:
                return True
        return None


__all__ = ["DeliveryStage", "DeliveryOrchestrator"]
