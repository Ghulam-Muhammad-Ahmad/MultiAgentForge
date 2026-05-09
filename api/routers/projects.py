import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Project, Board, Column, Agent
from models.column import COLUMN_NAMES
from schemas.common import ProjectCreate, ProjectUpdate, ProjectOut
from workers.workspace import init_workspace
from ws import manager

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(body: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = Project(id=str(uuid.uuid4()), **body.model_dump())
    db.add(project)
    await db.flush()

    board = Board(id=str(uuid.uuid4()), project_id=project.id)
    db.add(board)
    await db.flush()

    for i, name in enumerate(COLUMN_NAMES):
        db.add(Column(id=str(uuid.uuid4()), board_id=board.id, name=name, position=i))

    for role, name in [("pm", "PM Agent"), ("frontend", "Frontend Agent"), ("seo", "SEO Agent"), ("backend", "Backend Agent"), ("qa", "QA Agent"), ("build", "Build Verifier"), ("copy", "Copy Agent"), ("design_review", "Design Review Agent")]:
        db.add(Agent(id=str(uuid.uuid4()), project_id=project.id, role=role, name=name))

    await db.commit()
    await db.refresh(project)
    await manager.broadcast("project.created", {"project_id": project.id, "name": project.name})
    init_workspace.delay(project.id)
    await manager.broadcast("workspace.initialization_queued", {"project_id": project.id})
    return project


@router.get("/active", response_model=ProjectOut)
async def get_active_project(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.status == "active").limit(1))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "No active project")
    return project


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(project_id: str, body: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(project, k, v)
    await db.commit()
    await db.refresh(project)
    return project
