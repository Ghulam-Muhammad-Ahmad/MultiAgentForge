"""Delivery report, project export, and final presentation."""
import io
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Project, Board, Ticket, ProjectFile, RequirementDocument
from models.column import Column as ColumnModel
from config import settings
from ws import manager

router = APIRouter(prefix="/projects/{project_id}", tags=["delivery"])


@router.get("/delivery")
async def get_delivery_report(project_id: str, db: AsyncSession = Depends(get_db)):
    project_result = await db.execute(select(Project).where(Project.id == project_id))
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    board_result = await db.execute(
        select(Board).where(Board.project_id == project_id)
    )
    board = board_result.scalar_one_or_none()

    tickets_by_status: dict[str, int] = {}
    total_tickets = 0
    if board:
        tickets_result = await db.execute(
            select(Ticket).where(Ticket.board_id == board.id)
        )
        for ticket in tickets_result.scalars().all():
            tickets_by_status[ticket.status] = tickets_by_status.get(ticket.status, 0) + 1
            total_tickets += 1

    files_result = await db.execute(
        select(ProjectFile).where(ProjectFile.project_id == project_id)
    )
    files = files_result.scalars().all()

    req_result = await db.execute(
        select(RequirementDocument).where(RequirementDocument.project_id == project_id).limit(1)
    )
    req_doc = req_result.scalar_one_or_none()

    workspace = Path(settings.workspace_base_path) / f"project-{project_id}" / "astro-site"
    workspace_exists = workspace.exists()

    return {
        "project_id": project_id,
        "project_name": project.name,
        "project_status": project.status,
        "tickets_total": total_tickets,
        "tickets_by_status": tickets_by_status,
        "tickets_done": tickets_by_status.get("done", 0),
        "files_tracked": len(files),
        "file_list": [f.path for f in files],
        "requirement_summary": req_doc.summary if req_doc else None,
        "workspace_exists": workspace_exists,
    }


@router.post("/delivery/present")
async def mark_project_presented(project_id: str, db: AsyncSession = Depends(get_db)):
    """Move all Done tickets to Presented to User and mark project delivered."""
    board_result = await db.execute(
        select(Board).where(Board.project_id == project_id)
    )
    board = board_result.scalar_one_or_none()
    if not board:
        raise HTTPException(404, "Board not found")

    cols_result = await db.execute(
        select(ColumnModel).where(ColumnModel.board_id == board.id)
    )
    cols = cols_result.scalars().all()
    col_map = {col.name: col for col in cols}

    done_col = col_map.get("Done")
    presented_col = col_map.get("Presented to User")
    if not done_col or not presented_col:
        raise HTTPException(400, "Board columns not set up correctly")

    done_tickets_result = await db.execute(
        select(Ticket).where(
            Ticket.board_id == board.id,
            Ticket.column_id == done_col.id,
        )
    )
    moved = 0
    for ticket in done_tickets_result.scalars().all():
        ticket.column_id = presented_col.id
        ticket.status = "presented"
        moved += 1

    project_result = await db.execute(select(Project).where(Project.id == project_id))
    project = project_result.scalar_one_or_none()
    if project:
        project.status = "delivered"

    await db.commit()
    await manager.broadcast("project.delivered", {"project_id": project_id, "tickets_presented": moved})
    return {"moved": moved, "status": "delivered"}


@router.get("/export")
async def export_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Stream the Astro workspace as a ZIP file."""
    project_result = await db.execute(select(Project).where(Project.id == project_id))
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    workspace = Path(settings.workspace_base_path) / f"project-{project_id}" / "astro-site"
    if not workspace.exists():
        raise HTTPException(404, "Workspace not found — run PM Agent and agents first")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in workspace.rglob("*"):
            if file_path.is_file():
                # Skip node_modules and build output
                parts = file_path.parts
                if "node_modules" in parts or "dist" in parts or ".astro" in parts:
                    continue
                arcname = file_path.relative_to(workspace)
                zf.write(file_path, arcname)

    buf.seek(0)
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in project.name)
    filename = f"{safe_name}-astro-site.zip"

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
