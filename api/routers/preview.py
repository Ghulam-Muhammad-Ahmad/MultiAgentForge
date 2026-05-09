from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Project
from ws import manager

router = APIRouter(prefix="/projects/{project_id}/preview", tags=["preview"])


@router.post("/start")
async def start_preview(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Project not found")

    from workers.celery_app import celery_app
    task = celery_app.send_task("workers.preview_worker.start_preview", args=[project_id])
    await manager.broadcast("preview.started", {"project_id": project_id, "task_id": task.id})
    return {"task_id": task.id, "status": "starting"}


@router.post("/stop")
async def stop_preview(project_id: str):
    from workers.celery_app import celery_app
    celery_app.send_task("workers.preview_worker.stop_preview", args=[project_id])
    return {"status": "stopping"}


@router.get("/status")
async def preview_status(project_id: str):
    import redis as redis_lib
    from config import settings
    r = redis_lib.from_url(settings.redis_url)
    status = r.get(f"preview:status:{project_id}")
    port = r.get(f"preview:port:{project_id}")
    return {
        "status": status.decode() if status else "stopped",
        "port": int(port.decode()) if port else None,
    }


@router.get("/logs")
async def preview_logs(project_id: str):
    import redis as redis_lib
    from config import settings
    r = redis_lib.from_url(settings.redis_url)
    logs = r.lrange(f"preview:logs:{project_id}", 0, 200)
    return {"logs": [l.decode() for l in logs]}
