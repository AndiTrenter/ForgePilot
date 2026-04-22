"""Integration-Tests für den Delivery-Layer auf dem laufenden Backend.

Deckt ab:
- Delivery-Job wird bei erstem Chat-Request erstellt
- REST-Endpoints /api/delivery/*
- Policy-Engine-Evaluate-Action via REST
- Approval-Flow via REST (approve / reject)
- Meta-Block-Parser Regression (_extract_delivery_meta / _strip_delivery_meta)
- Regression: get /api/health bleibt intakt
"""
import os
import sys
import asyncio
import pathlib
import pytest
import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

BASE = os.environ.get("FP_BASE_URL", "http://localhost:8001")


# ----- Regression: API health darf nicht brechen ----------------------------

def test_health_endpoint_still_works():
    r = httpx.get(f"{BASE}/api/health", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "healthy"
    assert data.get("checks", {}).get("mongodb") is True


def test_version_endpoint_still_works():
    r = httpx.get(f"{BASE}/api/version", timeout=10)
    assert r.status_code == 200


# ----- Policy-Engine via REST -----------------------------------------------

def test_policy_engine_rest_auto():
    r = httpx.post(
        f"{BASE}/api/delivery/jobs/smoke/evaluate-action",
        json={"action": "build_app"},
        timeout=10,
    )
    assert r.status_code == 200
    d = r.json()
    assert d["category"] == "auto"
    assert d["allowed"] is True
    assert d["requires_approval"] is False


def test_policy_engine_rest_approval():
    r = httpx.post(
        f"{BASE}/api/delivery/jobs/smoke/evaluate-action",
        json={"action": "deploy_production"},
        timeout=10,
    )
    d = r.json()
    assert d["category"] == "approval"
    assert d["requires_approval"] is True


def test_policy_engine_rest_forbidden():
    r = httpx.post(
        f"{BASE}/api/delivery/jobs/smoke/evaluate-action",
        json={"action": "wipe_database"},
        timeout=10,
    )
    d = r.json()
    assert d["category"] == "forbidden"
    assert d["allowed"] is False


# ----- Meta-Parser Regression -----------------------------------------------

def test_meta_extract_and_strip():
    from server import _extract_delivery_meta, _strip_delivery_meta
    text = (
        "Hier ist mein Plan zum Feature.\n\n"
        '---DELIVERY_META---\n'
        '{"stage": "plan", "summary": "Plan steht", "needs_approval": false, '
        '"preview_url": null, "preview_checks": [], "user_question": null}\n'
        '---END_DELIVERY_META---\n'
    )
    meta = _extract_delivery_meta(text)
    assert meta["stage"] == "plan"
    assert meta["summary"] == "Plan steht"
    cleaned = _strip_delivery_meta(text)
    assert "DELIVERY_META" not in cleaned
    assert "Hier ist mein Plan" in cleaned


def test_meta_extract_none_when_missing():
    from server import _extract_delivery_meta
    assert _extract_delivery_meta("Nur freier Text ohne Meta-Block.") is None


def test_meta_extract_last_wins():
    from server import _extract_delivery_meta
    text = (
        "---DELIVERY_META---\n"
        '{"stage": "plan"}\n'
        "---END_DELIVERY_META---\n"
        "Später update:\n"
        "---DELIVERY_META---\n"
        '{"stage": "build", "summary": "updated"}\n'
        "---END_DELIVERY_META---\n"
    )
    meta = _extract_delivery_meta(text)
    assert meta["stage"] == "build"
    assert meta["summary"] == "updated"


# ----- Delivery Job Lifecycle via Orchestrator direkt -----------------------

def test_orchestrator_lifecycle_on_real_mongo():
    """Greift direkt auf den in server.py initialisierten Orchestrator zu."""
    from server import delivery_orchestrator
    from deploy_orchestrator import DeliveryStage

    async def run():
        jid = await delivery_orchestrator.create_job(
            project_id="itest-proj",
            session_id="itest-sess",
            user_id="itest-user",
            request_text="Integration test",
        )
        try:
            for s in [
                DeliveryStage.PLAN,
                DeliveryStage.BUILD,
                DeliveryStage.VERIFY,
            ]:
                await delivery_orchestrator.update_stage(jid, s)
            await delivery_orchestrator.set_preview(
                jid,
                "http://preview.local/itest",
                checks=["Loads", "Login works", "Save works"],
                summary="Preview ready",
            )
            await delivery_orchestrator.request_approval(
                jid, summary="Bitte testen"
            )
            await delivery_orchestrator.set_approval(
                jid, approved=True, approved_by="itest-user"
            )
            await delivery_orchestrator.finalize_job(
                jid, result={"deployed": True}
            )
            final = await delivery_orchestrator.get_job(jid)
            assert final["stage"] == DeliveryStage.DONE.value
            assert final["preview_url"] == "http://preview.local/itest"
            assert final["approved"] is True
            return jid
        finally:
            # Cleanup
            await delivery_orchestrator.coll.delete_one({"job_id": jid})

    asyncio.get_event_loop().run_until_complete(run())


def test_approve_endpoint_requires_awaiting_approval_stage():
    """REST /approve soll bei falscher Stage 409 zurückgeben."""
    from server import delivery_orchestrator

    async def setup():
        jid = await delivery_orchestrator.create_job("itest-reject", None, None, "x")
        return jid

    jid = asyncio.get_event_loop().run_until_complete(setup())
    try:
        r = httpx.post(
            f"{BASE}/api/delivery/jobs/{jid}/approve",
            json={"approved_by": "tester"},
            timeout=10,
        )
        assert r.status_code == 409
    finally:
        async def cleanup():
            await delivery_orchestrator.coll.delete_one({"job_id": jid})
        asyncio.get_event_loop().run_until_complete(cleanup())


def test_get_delivery_jobs_empty_project():
    """Projekte ohne Jobs liefern active=None, history=[]."""
    r = httpx.get(f"{BASE}/api/delivery/jobs/nonexistent-project-xyz", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data["active"] is None
    assert data["history"] == []
