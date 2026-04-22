"""Unit-Tests für backend.deploy_orchestrator - nutzt mongomock."""
import sys
import pathlib
import asyncio
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from deploy_orchestrator import DeliveryOrchestrator, DeliveryStage  # noqa: E402


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *args, **kwargs):
        # Wir tun so, als sei die Reihenfolge stabil - für Tests reicht das.
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    async def to_list(self, n):
        return self._docs[:n]


class _FakeCollection:
    """Minimales async-Motor-Replacement, genug für Orchestrator-Tests."""

    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        self.docs.append(doc)
        return type("R", (), {"inserted_id": doc.get("job_id")})

    async def find_one(self, filt, projection=None, sort=None):
        matches = [d for d in self.docs if _match(d, filt)]
        if sort:
            for key, direction in reversed(sort):
                matches.sort(key=lambda x: x.get(key), reverse=(direction == -1))
        return _project(matches[0], projection) if matches else None

    def find(self, filt, projection=None):
        matches = [d for d in self.docs if _match(d, filt)]
        return _FakeCursor([_project(m, projection) for m in matches])

    async def update_one(self, filt, update):
        for d in self.docs:
            if _match(d, filt):
                if "$set" in update:
                    for k, v in update["$set"].items():
                        d[k] = v
                if "$push" in update:
                    for k, v in update["$push"].items():
                        d.setdefault(k, []).append(v)
                return


def _match(doc, filt):
    for k, v in filt.items():
        if isinstance(v, dict) and "$nin" in v:
            if doc.get(k) in v["$nin"]:
                return False
        else:
            if doc.get(k) != v:
                return False
    return True


def _project(doc, projection):
    if not projection:
        return dict(doc)
    if projection.get("_id") == 0:
        return {k: v for k, v in doc.items() if k != "_id"}
    return dict(doc)


class _FakeDB:
    def __init__(self):
        self._colls = {}

    def __getitem__(self, name):
        self._colls.setdefault(name, _FakeCollection())
        return self._colls[name]


@pytest.fixture
def orch():
    return DeliveryOrchestrator(_FakeDB())


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_happy_path(orch):
    async def flow():
        jid = await orch.create_job("proj-1", "sess-1", "user-1", "Baue eine Todo-App")
        job = await orch.get_job(jid)
        assert job["stage"] == DeliveryStage.REQUIREMENTS.value

        await orch.update_stage(jid, DeliveryStage.PLAN)
        await orch.update_stage(jid, DeliveryStage.BUILD)
        await orch.update_stage(jid, DeliveryStage.VERIFY)
        await orch.set_preview(jid, "http://preview.local/1", checks=["Login geht", "Save geht"])
        assert (await orch.get_job(jid))["stage"] == DeliveryStage.PREVIEW_READY.value

        await orch.request_approval(jid, summary="Feature fertig, bitte testen.")
        assert (await orch.get_job(jid))["stage"] == DeliveryStage.AWAITING_APPROVAL.value

        await orch.set_approval(jid, approved=True, approved_by="user:test")
        assert (await orch.get_job(jid))["stage"] == DeliveryStage.DEPLOYING.value

        final = await orch.finalize_job(jid, result={"deployed": True, "url": "http://prod/1"})
        assert final["stage"] == DeliveryStage.DONE.value
        assert final["result"]["deployed"] is True

    run(flow())


def test_invalid_transition_rejected(orch):
    async def flow():
        jid = await orch.create_job("proj-2", None, None, "test")
        # REQUIREMENTS -> DEPLOYING ist illegal
        with pytest.raises(ValueError):
            await orch.update_stage(jid, DeliveryStage.DEPLOYING)

    run(flow())


def test_rejection_path(orch):
    async def flow():
        jid = await orch.create_job("proj-3", None, None, "test")
        for s in [
            DeliveryStage.PLAN,
            DeliveryStage.BUILD,
            DeliveryStage.VERIFY,
            DeliveryStage.PREVIEW_READY,
        ]:
            await orch.update_stage(jid, s)
        await orch.request_approval(jid, summary="bitte testen")
        await orch.set_approval(jid, approved=False, approved_by="user:test", reason="Bug gefunden")
        job = await orch.get_job(jid)
        assert job["stage"] == DeliveryStage.REJECTED.value
        assert job["rejected_reason"] == "Bug gefunden"

    run(flow())


def test_detect_approval_keywords():
    assert DeliveryOrchestrator.detect_approval("bitte freigeben") is True
    assert DeliveryOrchestrator.detect_approval("jetzt deploy machen") is True
    assert DeliveryOrchestrator.detect_approval("noch nicht freigeben") is False
    assert DeliveryOrchestrator.detect_approval("mach das größer") is None
    assert DeliveryOrchestrator.detect_approval("") is None


def test_block_from_any_stage(orch):
    async def flow():
        jid = await orch.create_job("proj-4", None, None, "test")
        await orch.update_stage(jid, DeliveryStage.PLAN)
        await orch.block(jid, reason="OpenAI down")
        job = await orch.get_job(jid)
        assert job["stage"] == DeliveryStage.BLOCKED.value

    run(flow())


def test_get_active_job(orch):
    async def flow():
        j1 = await orch.create_job("proj-5", None, None, "A")
        # terminal machen
        for s in [
            DeliveryStage.PLAN,
            DeliveryStage.BUILD,
            DeliveryStage.VERIFY,
            DeliveryStage.PREVIEW_READY,
            DeliveryStage.AWAITING_APPROVAL,
            DeliveryStage.DEPLOYING,
            DeliveryStage.DONE,
        ]:
            await orch.update_stage(j1, s)
        j2 = await orch.create_job("proj-5", None, None, "B")
        active = await orch.get_active_job("proj-5")
        assert active is not None
        assert active["job_id"] == j2

    run(flow())
