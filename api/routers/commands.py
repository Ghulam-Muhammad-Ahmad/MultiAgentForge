from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import CommandExecution
from schemas.common import CommandOut
from ws import manager
from agents.command_runner import send_approval_signal

router = APIRouter(tags=["commands"])


@router.get("/commands/{command_id}", response_model=CommandOut)
async def get_command(command_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CommandExecution).where(CommandExecution.id == command_id))
    cmd = result.scalar_one_or_none()
    if not cmd:
        raise HTTPException(404, "Command not found")
    return cmd


@router.post("/commands/{command_id}/approve", response_model=CommandOut)
async def approve_command(command_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CommandExecution).where(CommandExecution.id == command_id))
    cmd = result.scalar_one_or_none()
    if not cmd:
        raise HTTPException(404, "Command not found")
    if cmd.status != "pending":
        raise HTTPException(400, f"Command status is '{cmd.status}', cannot approve")
    cmd.status = "approved"
    await db.commit()
    await db.refresh(cmd)
    await send_approval_signal(command_id, "approved")
    await manager.broadcast("command.approved", {"command_id": command_id})
    return cmd


@router.post("/commands/{command_id}/reject", response_model=CommandOut)
async def reject_command(command_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CommandExecution).where(CommandExecution.id == command_id))
    cmd = result.scalar_one_or_none()
    if not cmd:
        raise HTTPException(404, "Command not found")
    if cmd.status != "pending":
        raise HTTPException(400, f"Command status is '{cmd.status}', cannot reject")
    cmd.status = "rejected"
    await db.commit()
    await db.refresh(cmd)
    await send_approval_signal(command_id, "rejected")
    await manager.broadcast("command.rejected", {"command_id": command_id})
    return cmd


@router.get("/commands/{command_id}/logs")
async def get_command_logs(command_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CommandExecution).where(CommandExecution.id == command_id))
    cmd = result.scalar_one_or_none()
    if not cmd:
        raise HTTPException(404, "Command not found")
    return {"stdout": cmd.stdout, "stderr": cmd.stderr, "exit_code": cmd.exit_code}


@router.get("/projects/{project_id}/commands", response_model=list[CommandOut])
async def list_project_commands(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CommandExecution).where(CommandExecution.project_id == project_id).order_by(CommandExecution.created_at.desc()).limit(100)
    )
    return result.scalars().all()
