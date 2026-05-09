from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Agent, AgentRun, Ticket
from schemas.common import AgentOut, AgentRunOut

router = APIRouter(tags=["agents"])


@router.get("/projects/{project_id}/agents", response_model=list[AgentOut])
async def list_agents(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.project_id == project_id))
    return result.scalars().all()


@router.post("/agents/{agent_id}/run")
async def trigger_agent_run(agent_id: str, ticket_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")

    from workers.celery_app import celery_app
    task = celery_app.send_task("workers.orchestrator.run_agent", args=[agent_id, ticket_id])
    return {"task_id": task.id, "status": "queued"}


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str, db: AsyncSession = Depends(get_db)):
    run_result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    if run.status not in ("running", "queued"):
        raise HTTPException(400, f"Run status '{run.status}' cannot be cancelled")

    run.status = "cancelled"

    agent_result = await db.execute(select(Agent).where(Agent.id == run.agent_id))
    agent = agent_result.scalar_one_or_none()
    if agent:
        agent.status = "idle"

    ticket_result = await db.execute(select(Ticket).where(Ticket.id == run.ticket_id))
    ticket = ticket_result.scalar_one_or_none()
    if ticket:
        ticket.status = "ready"

    await db.commit()

    from workers.event_bus import publish
    publish("agent.run.cancelled", {"run_id": run_id, "agent_id": run.agent_id, "ticket_id": run.ticket_id})

    return {"status": "cancelled"}


@router.post("/runs/{run_id}/retry")
async def retry_run(run_id: str, db: AsyncSession = Depends(get_db)):
    run_result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    if run.status not in ("failed", "cancelled", "completed"):
        raise HTTPException(400, f"Run status '{run.status}' cannot be retried")

    ticket_result = await db.execute(select(Ticket).where(Ticket.id == run.ticket_id))
    ticket = ticket_result.scalar_one_or_none()
    if ticket:
        ticket.status = "ready"

    agent_result = await db.execute(select(Agent).where(Agent.id == run.agent_id))
    agent = agent_result.scalar_one_or_none()
    if agent:
        agent.status = "idle"

    await db.commit()

    from workers.celery_app import celery_app
    task = celery_app.send_task("workers.orchestrator.run_agent", args=[run.agent_id, run.ticket_id])
    return {"task_id": task.id, "status": "queued"}


@router.get("/agents/{agent_id}/runs", response_model=list[AgentRunOut])
async def list_agent_runs(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentRun).where(AgentRun.agent_id == agent_id).order_by(AgentRun.created_at.desc()).limit(50)
    )
    return result.scalars().all()


@router.get("/projects/{project_id}/runs", response_model=list[AgentRunOut])
async def list_project_runs(project_id: str, db: AsyncSession = Depends(get_db)):
    """All agent runs across all agents for a project, newest first."""
    agents_result = await db.execute(select(Agent.id).where(Agent.project_id == project_id))
    agent_ids = [r[0] for r in agents_result.all()]
    if not agent_ids:
        return []
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.agent_id.in_(agent_ids))
        .order_by(AgentRun.created_at.desc())
        .limit(200)
    )
    return result.scalars().all()
