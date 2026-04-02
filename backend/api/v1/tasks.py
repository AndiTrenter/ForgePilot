"""
Task Management API
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime, timezone
from uuid import uuid4

from core import get_database, StateMachine, TaskStatus
from models import Task, TaskCreate, TaskUpdate
from gates import enforce_completion_gate
from api.dependencies import get_db

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=Task)
async def create_task(
    task_data: TaskCreate,
    db = Depends(get_db)
):
    """Erstellt neuen Task"""
    task = Task(
        id=str(uuid4()),
        project_id=task_data.project_id,
        name=task_data.name,
        description=task_data.description,
        type=task_data.type,
        priority=task_data.priority,
        acceptance_criteria=[
            {"id": str(uuid4()), "description": ac, "met": False}
            for ac in task_data.acceptance_criteria
        ],
        depends_on=task_data.depends_on,
        assigned_agent=task_data.assigned_agent,
        estimated_effort=task_data.estimated_effort,
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat()
    )
    
    await db.tasks.insert_one(task.model_dump())
    return task


@router.get("/project/{project_id}", response_model=List[Task])
async def list_project_tasks(
    project_id: str,
    status: Optional[TaskStatus] = None,
    db = Depends(get_db)
):
    """Listet Tasks eines Projekts"""
    query = {"project_id": project_id}
    if status:
        query["status"] = status.value
    
    tasks = await db.tasks.find(query, {"_id": 0}).to_list(1000)
    return [Task(**t) for t in tasks]


@router.get("/{task_id}", response_model=Task)
async def get_task(
    task_id: str,
    db = Depends(get_db)
):
    """Holt Task-Details"""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return Task(**task)


@router.put("/{task_id}", response_model=Task)
async def update_task(
    task_id: str,
    update_data: TaskUpdate,
    db = Depends(get_db)
):
    """Aktualisiert Task"""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_obj = Task(**task)
    
    # Status-Transition prüfen
    if update_data.status and update_data.status != task_obj.status:
        sm = StateMachine()
        await sm.transition_task(
            task_id,
            task_obj.status,
            update_data.status,
            reason="Manual update"
        )
    
    # Update-Daten anwenden
    update_dict = update_data.model_dump(exclude_unset=True)
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.tasks.update_one(
        {"id": task_id},
        {"$set": update_dict}
    )
    
    updated_task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    return Task(**updated_task)


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: str,
    db = Depends(get_db)
):
    """Schließt Task ab (mit Gate-Prüfung)"""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_obj = Task(**task)
    
    # Completion-Gates prüfen
    try:
        gate_report = await enforce_completion_gate(task_obj)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    
    # Status auf DONE setzen
    await db.tasks.update_one(
        {"id": task_id},
        {"$set": {
            "status": TaskStatus.DONE.value,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "success": True,
        "message": "Task completed",
        "gate_report": gate_report
    }


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    db = Depends(get_db)
):
    """Löscht Task"""
    result = await db.tasks.delete_one({"id": task_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "message": "Task deleted"}
