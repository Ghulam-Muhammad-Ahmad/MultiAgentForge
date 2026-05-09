import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Project, RequirementDocument
from schemas.common import RequirementCreate, RequirementOut
from ws import manager

router = APIRouter(prefix="/projects/{project_id}/requirements", tags=["requirements"])


@router.post("", response_model=RequirementOut, status_code=201)
async def upload_requirement(project_id: str, body: RequirementCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Project not found")

    doc = RequirementDocument(id=str(uuid.uuid4()), project_id=project_id, **body.model_dump())
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    await manager.broadcast("requirement.uploaded", {"project_id": project_id, "doc_id": doc.id})
    return doc


@router.get("", response_model=list[RequirementOut])
async def list_requirements(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RequirementDocument).where(RequirementDocument.project_id == project_id))
    return result.scalars().all()


@router.post("/analyze")
async def analyze_requirements(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RequirementDocument).where(RequirementDocument.project_id == project_id).order_by(RequirementDocument.created_at.desc()).limit(1)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "No requirement document found")

    from workers.celery_app import celery_app
    task = celery_app.send_task("workers.orchestrator.run_pm_agent", args=[project_id, doc.id])
    await manager.broadcast("requirement.analyzed", {"project_id": project_id, "task_id": task.id})
    return {"task_id": task.id, "status": "queued"}
