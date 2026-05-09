import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Ticket, TicketComment, Board, Agent
from schemas.common import TicketCreate, TicketUpdate, TicketOut, CommentCreate, CommentOut
from ws import manager

router = APIRouter(tags=["tickets"])


@router.post("/boards/{board_id}/tickets", response_model=TicketOut, status_code=201)
async def create_ticket(board_id: str, body: TicketCreate, db: AsyncSession = Depends(get_db)):
    data = body.model_dump()

    # Resolve agent_role → assigned_agent_id
    assigned_agent_id = None
    if data.get("agent_role"):
        board_result = await db.execute(select(Board).where(Board.id == board_id))
        board = board_result.scalar_one_or_none()
        if board:
            agent_result = await db.execute(
                select(Agent).where(
                    Agent.project_id == board.project_id,
                    Agent.role == data["agent_role"],
                )
            )
            agent = agent_result.scalar_one_or_none()
            if agent:
                assigned_agent_id = agent.id

    ticket = Ticket(id=str(uuid.uuid4()), board_id=board_id, assigned_agent_id=assigned_agent_id, **data)
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    await manager.broadcast("ticket.created", {"ticket_id": ticket.id, "board_id": board_id, "title": ticket.title, "agent_role": ticket.agent_role})

    # Auto-dispatch if agent resolved
    if assigned_agent_id:
        from workers.celery_app import celery_app
        celery_app.send_task(
            "workers.orchestrator.run_agent",
            args=[assigned_agent_id, ticket.id],
        )

    return ticket


@router.get("/tickets/{ticket_id}", response_model=TicketOut)
async def get_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return ticket


@router.patch("/tickets/{ticket_id}", response_model=TicketOut)
async def update_ticket(ticket_id: str, body: TicketUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(ticket, k, v)
    await db.commit()
    await db.refresh(ticket)
    await manager.broadcast("ticket.updated", {"ticket_id": ticket.id, "column_id": ticket.column_id})
    return ticket


@router.post("/tickets/{ticket_id}/comments", response_model=CommentOut, status_code=201)
async def add_comment(ticket_id: str, body: CommentCreate, db: AsyncSession = Depends(get_db)):
    comment = TicketComment(
        id=str(uuid.uuid4()),
        ticket_id=ticket_id,
        author_type="user",
        comment=body.comment,
        visibility=body.visibility,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    await manager.broadcast("ticket.comment.created", {"ticket_id": ticket_id, "comment_id": comment.id})
    return comment


@router.post("/tickets/{ticket_id}/run")
async def run_ticket_agent(ticket_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    if not ticket.assigned_agent_id:
        raise HTTPException(400, "No agent assigned to this ticket")

    from workers.celery_app import celery_app
    task = celery_app.send_task(
        "workers.orchestrator.run_agent",
        args=[ticket.assigned_agent_id, ticket_id],
    )
    return {"task_id": task.id, "status": "queued"}


@router.get("/tickets/{ticket_id}/comments", response_model=list[CommentOut])
async def list_comments(ticket_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TicketComment).where(TicketComment.ticket_id == ticket_id).order_by(TicketComment.created_at)
    )
    return result.scalars().all()
