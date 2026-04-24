"""Integration-Test: Re-Open nach mark_complete.

Stellt sicher:
- Ein als 'ready_for_push' markiertes Projekt wird bei neuer Chat-Nachricht
  wieder auf 'iterating' gesetzt.
- Ein Iteration-Hinweis (system-role message) wird in der Message-Historie
  eingefügt.
- Neuer Delivery-Job wird angelegt.
"""
import os
import sys
import asyncio
import pathlib
import uuid
import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

BASE = os.environ.get("FP_BASE_URL", "http://localhost:8001")


def _stream_one_chunk(project_id: str, content: str, timeout: float = 8.0):
    """Startet einen SSE-Chat-Request und verwirft Stream-Inhalt nach 1. Chunk."""
    with httpx.stream(
        "POST",
        f"{BASE}/api/projects/{project_id}/chat",
        json={"content": content, "role": "user"},
        timeout=timeout,
    ) as r:
        assert r.status_code == 200
        for _ in r.iter_lines():
            # Erster Chunk reicht, dann abbrechen - Server-Side lief der
            # Re-Open-Branch bereits durch (vor dem SSE-Stream).
            break


def test_reopen_after_mark_complete_resets_status_and_creates_new_job():
    from server import delivery_orchestrator  # noqa

    # 1) Projekt anlegen
    proj_resp = httpx.post(
        f"{BASE}/api/projects",
        json={
            "name": f"reopen-test-{uuid.uuid4().hex[:6]}",
            "description": "Re-open regression",
            "project_type": "fullstack",
        },
        timeout=10,
    )
    assert proj_resp.status_code == 200
    project_id = proj_resp.json()["id"]

    try:
        # 2) Status manuell auf ready_for_push setzen (simuliert mark_complete)
        async def simulate_complete():
            from server import db
            await db.projects.update_one(
                {"id": project_id},
                {
                    "$set": {
                        "status": "ready_for_push",
                        "pending_commit_message": "Feature X fertig",
                    }
                },
            )
            # Auch einen "fertig"-Log einfügen
            from server import Message
            msg = Message(
                project_id=project_id,
                content="✅ PROJEKT FERTIG!\nFeature X erledigt.",
                role="assistant",
                agent_type="orchestrator",
            )
            await db.messages.insert_one(msg.model_dump())

        asyncio.get_event_loop().run_until_complete(simulate_complete())

        # 3) Neue Chat-Nachricht senden ("Parallax-Effekt hinzufügen")
        try:
            _stream_one_chunk(project_id, "Bitte Parallax-Effekt hinzufügen")
        except httpx.ReadTimeout:
            pass  # Stream brauchen wir nicht vollständig

        # Kurz warten, damit DB-Write durch ist
        import time
        time.sleep(0.3)

        # 4) Verify: Status = iterating, neue system-message vorhanden, neuer Job aktiv
        async def verify():
            from server import db
            proj = await db.projects.find_one({"id": project_id})
            assert proj["status"] == "iterating", f"Status ist {proj['status']}, erwartet 'iterating'"
            assert proj.get("pending_commit_message") is None
            assert proj.get("iteration_count", 0) >= 1

            # System-Message mit Iteration-Hinweis?
            msgs = await db.messages.find(
                {"project_id": project_id, "role": "system"}
            ).to_list(10)
            assert any("Neue Iteration" in m.get("content", "") for m in msgs), \
                "Iteration-Hinweis fehlt in messages"

            # Neuer Delivery-Job aktiv?
            active = await delivery_orchestrator.get_active_job(project_id)
            assert active is not None, "Kein aktiver Delivery-Job nach Re-Open"
            assert active["stage"] == "requirements", \
                f"Neuer Job steht auf {active['stage']}, erwartet 'requirements'"
            return active["job_id"]

        jid = asyncio.get_event_loop().run_until_complete(verify())
        assert jid, "Kein job_id"

    finally:
        # Cleanup
        httpx.delete(f"{BASE}/api/projects/{project_id}", timeout=10)
