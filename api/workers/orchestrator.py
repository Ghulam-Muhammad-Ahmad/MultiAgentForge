import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload

from config import settings
from models import Agent, Board, Column, RequirementDocument, Project, Ticket, AgentRun
from workers.celery_app import celery_app
from workers.event_bus import publish


@asynccontextmanager
async def _task_db():
    """Create a fresh DB engine per Celery task to avoid asyncpg/fork event-loop issues."""
    engine = create_async_engine(
        settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# PM Agent task
# ---------------------------------------------------------------------------

@celery_app.task(name="workers.orchestrator.run_pm_agent", bind=True)
def run_pm_agent(self, project_id: str, doc_id: str):
    asyncio.run(_run_pm_agent(project_id, doc_id))


async def _run_pm_agent(project_id: str, doc_id: str) -> None:
    async with _task_db() as db:
        doc_result = await db.execute(
            select(RequirementDocument).where(RequirementDocument.id == doc_id)
        )
        doc = doc_result.scalar_one_or_none()
        if not doc:
            publish("agent.run.failed", {"project_id": project_id, "error": "Requirement document not found"})
            return

        project_result = await db.execute(select(Project).where(Project.id == project_id))
        project = project_result.scalar_one_or_none()
        if not project:
            publish("agent.run.failed", {"project_id": project_id, "error": "Project not found"})
            return

        pm_result = await db.execute(
            select(Agent).where(Agent.project_id == project_id, Agent.role == "pm")
        )
        pm_agent = pm_result.scalar_one_or_none()
        if pm_agent:
            pm_agent.status = "running"
            await db.commit()

        publish("agent.run.started", {"project_id": project_id, "role": "pm"})

        try:
            from workers.workspace import _init_workspace
            await _init_workspace(project_id)
            from agents.pm_agent import analyze_requirements
            analysis = await analyze_requirements(doc.raw_content, project.name, project_id)
        except Exception as exc:
            if pm_agent:
                pm_agent.status = "error"
                await db.commit()
            publish("agent.run.failed", {"project_id": project_id, "error": str(exc)})
            raise

        doc.summary = analysis.project_summary
        doc.parsed_content = _format_parsed_content(analysis)
        await db.commit()

        publish("requirement.analyzed", {"project_id": project_id, "summary": analysis.project_summary})

        board_result = await db.execute(
            select(Board)
            .where(Board.project_id == project_id)
            .options(selectinload(Board.columns))
        )
        board = board_result.scalar_one_or_none()
        if not board:
            publish("agent.run.failed", {"project_id": project_id, "error": "Board not found"})
            return

        column_map: dict[str, Column] = {col.name: col for col in board.columns}
        ready_col = column_map.get("Ready") or column_map.get("Backlog")
        if not ready_col:
            return

        agents_result = await db.execute(select(Agent).where(Agent.project_id == project_id))
        agents_by_role: dict[str, Agent] = {a.role: a for a in agents_result.scalars().all()}

        title_to_id: dict[str, str] = {spec.title: str(uuid.uuid4()) for spec in analysis.tickets}

        created_tickets: list[Ticket] = []
        for spec in analysis.tickets:
            ticket_id = title_to_id[spec.title]
            assigned_agent = agents_by_role.get(spec.agent_role)
            dep_ids = [title_to_id[t] for t in spec.dependencies if t in title_to_id]

            ticket = Ticket(
                id=ticket_id,
                board_id=board.id,
                column_id=ready_col.id,
                title=spec.title,
                description=spec.description,
                acceptance_criteria=spec.acceptance_criteria,
                assigned_agent_id=assigned_agent.id if assigned_agent else None,
                agent_role=spec.agent_role,
                status="ready",
                priority=spec.priority,
                files_affected=spec.files_affected,
                dependencies=dep_ids,
                created_by_agent_id=pm_agent.id if pm_agent else None,
            )
            db.add(ticket)
            created_tickets.append(ticket)

        await db.commit()

        for ticket in created_tickets:
            publish("ticket.created", {
                "ticket_id": ticket.id,
                "board_id": board.id,
                "title": ticket.title,
                "agent_role": ticket.agent_role,
            })

        if pm_agent:
            pm_agent.status = "idle"
            await db.commit()

        publish("agent.run.completed", {
            "project_id": project_id,
            "role": "pm",
            "tickets_created": len(created_tickets),
        })

        # Auto-dispatch ready tickets after the PM plan is created.
        _dispatch_ready_tickets(project_id, created_tickets, agents_by_role)


def _dispatch_ready_tickets(
    project_id: str,
    tickets: list[Ticket],
    agents_by_role: dict[str, Agent],
) -> None:
    """Queue run_agent for each ticket with no dependencies."""
    for ticket in tickets:
        if ticket.assigned_agent_id and not ticket.dependencies:
            run_agent.delay(ticket.assigned_agent_id, ticket.id)


# ---------------------------------------------------------------------------
# Worker Agent task
# ---------------------------------------------------------------------------

@celery_app.task(name="workers.orchestrator.run_agent", bind=True)
def run_agent(self, agent_id: str, ticket_id: str):
    asyncio.run(_run_agent(agent_id, ticket_id))


async def _run_agent(agent_id: str, ticket_id: str) -> None:
    async with _task_db() as db:
        agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = agent_result.scalar_one_or_none()
        if not agent:
            return

        # Pre-check: if ticket.agent_role doesn't match agent.role, reroute
        ticket_result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
        ticket = ticket_result.scalar_one_or_none()
        if ticket and ticket.agent_role and ticket.agent_role != agent.role:
            correct_result = await db.execute(
                select(Agent).where(
                    Agent.project_id == agent.project_id,
                    Agent.role == ticket.agent_role,
                )
            )
            correct_agent = correct_result.scalar_one_or_none()
            if correct_agent:
                publish("ticket.rerouted", {
                    "ticket_id": ticket_id,
                    "from_role": agent.role,
                    "to_role": correct_agent.role,
                })
                run_agent.delay(correct_agent.id, ticket_id)
                return

        agent_instance = _get_agent_instance(agent.role)
        if not agent_instance:
            publish("agent.run.failed", {
                "agent_id": agent_id,
                "ticket_id": ticket_id,
                "error": f"No implementation for role: {agent.role}",
            })
            return

        await agent_instance.execute(db, ticket_id, agent_id)

        # After completion, check if any tickets had this as a dependency and queue them
        await _dispatch_unblocked_tickets(db, ticket_id)


async def _dispatch_unblocked_tickets(db, completed_ticket_id: str) -> None:
    """Find tickets that depended on completed_ticket_id and dispatch if all deps done."""
    from sqlalchemy import text
    result = await db.execute(
        select(Ticket).where(
            Ticket.status.in_(["ready", "backlog"]),
            Ticket.assigned_agent_id.isnot(None),
        )
    )
    candidates = result.scalars().all()

    for ticket in candidates:
        deps = ticket.dependencies or []
        if completed_ticket_id not in deps:
            continue
        # Check all deps are done
        if not deps:
            continue
        done_result = await db.execute(
            select(Ticket.id).where(
                Ticket.id.in_(deps),
                Ticket.status == "done",
            )
        )
        done_ids = {r[0] for r in done_result.all()}
        if set(deps) == done_ids:
            run_agent.delay(ticket.assigned_agent_id, ticket.id)


def _get_agent_instance(role: str):
    if role == "pm":
        from agents.pm_ticket_agent import PMTicketAgent
        return PMTicketAgent()
    if role == "frontend":
        from agents.frontend_agent import FrontendAgent
        return FrontendAgent()
    if role == "seo":
        from agents.seo_agent import SEOAgent
        return SEOAgent()
    if role == "backend":
        from agents.backend_agent import BackendAgent
        return BackendAgent()
    if role == "qa":
        from agents.qa_agent import QAAgent
        return QAAgent()
    if role == "build":
        from agents.build_agent import BuildAgent
        return BuildAgent()
    if role == "copy":
        from agents.copy_agent import CopyAgent
        return CopyAgent()
    if role == "design_review":
        from agents.design_review_agent import DesignReviewAgent
        return DesignReviewAgent()
    return None


def _format_parsed_content(analysis) -> str:
    lines = [
        f"# Project Summary\n{analysis.project_summary}",
        "\n## Pages\n" + "\n".join(f"- {p}" for p in analysis.pages_identified),
        "\n## Features\n" + "\n".join(f"- {f}" for f in analysis.features_identified),
        f"\n## Tickets Generated\n{len(analysis.tickets)} tickets created.",
    ]
    return "\n".join(lines)
