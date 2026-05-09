"""Astro preview worker — manages npm install + dev server lifecycle."""
import asyncio
import os
import signal
import subprocess
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import redis

from workers.celery_app import celery_app
from workers.event_bus import publish
from config import settings

PREVIEW_PORT = 4321
_LOG_KEY = "preview:logs:{}"
_STATUS_KEY = "preview:status:{}"
_PID_KEY = "preview:pid:{}"
_PORT_KEY = "preview:port:{}"
_MAX_LOG_LINES = 500


def _redis():
    return redis.from_url(settings.redis_url)


@asynccontextmanager
async def _task_db():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
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


async def _create_build_ticket(project_id: str, error_log: str) -> None:
    """Create a build-verify ticket when preview detects errors."""
    from sqlalchemy import select
    from models import Agent, Board, Column, Ticket

    async with _task_db() as db:
        board_result = await db.execute(
            select(Board).where(Board.project_id == project_id)
        )
        board = board_result.scalar_one_or_none()
        if not board:
            return

        # Find Ready column
        col_result = await db.execute(
            select(Column).where(Column.board_id == board.id, Column.name == "Ready")
        )
        ready_col = col_result.scalar_one_or_none()
        if not ready_col:
            return

        # Find build agent
        agent_result = await db.execute(
            select(Agent).where(Agent.project_id == project_id, Agent.role == "build")
        )
        build_agent = agent_result.scalar_one_or_none()

        # Avoid duplicate open build tickets
        existing_result = await db.execute(
            select(Ticket).where(
                Ticket.board_id == board.id,
                Ticket.agent_role == "build",
                Ticket.status.in_(["ready", "backlog", "in_progress"]),
            )
        )
        if existing_result.scalar_one_or_none():
            return  # Already a pending build ticket

        snippet = error_log.strip()[-2000:]
        ticket = Ticket(
            id=str(uuid.uuid4()),
            board_id=board.id,
            column_id=ready_col.id,
            title="Fix build errors detected during preview",
            description=(
                "Preview startup failed. Exact error output:\n\n"
                f"```\n{snippet}\n```\n\n"
                "Run npm install then npm run build. "
                "For each error create a fix ticket for the owning agent."
            ),
            acceptance_criteria=[
                "npm run build exits with code 0",
                "Preview dev server starts without errors",
            ],
            assigned_agent_id=build_agent.id if build_agent else None,
            agent_role="build",
            status="ready",
            priority="high",
            files_affected=[],
            dependencies=[],
        )
        db.add(ticket)
        await db.commit()

        publish("ticket.created", {
            "ticket_id": ticket.id,
            "board_id": board.id,
            "title": ticket.title,
            "agent_role": "build",
        })


def _push_log(r, project_id: str, line: str) -> None:
    key = _LOG_KEY.format(project_id)
    r.rpush(key, line)
    r.ltrim(key, -_MAX_LOG_LINES, -1)


def _kill_existing(r, project_id: str) -> None:
    pid_raw = r.get(_PID_KEY.format(project_id))
    if not pid_raw:
        return
    pid = int(pid_raw)
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except OSError:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    r.delete(_PID_KEY.format(project_id))


def _tail_logs(proc: subprocess.Popen, project_id: str, r) -> None:
    """Thread target: tail process stdout into Redis and detect ready signal."""
    ready_published = False
    for raw_line in proc.stdout:
        line = raw_line.rstrip()
        _push_log(r, project_id, line)
        if not ready_published:
            lower = line.lower()
            if ("localhost" in lower or "local" in lower) and (
                "4321" in line or "ready" in lower or "started" in lower
            ):
                r.set(_STATUS_KEY.format(project_id), "running")
                r.set(_PORT_KEY.format(project_id), PREVIEW_PORT)
                publish("preview.ready", {"project_id": project_id, "port": PREVIEW_PORT})
                ready_published = True

    exit_code = proc.wait()
    current = r.get(_STATUS_KEY.format(project_id))
    if current and current.decode() not in ("stopped", "error"):
        if exit_code != 0:
            r.set(_STATUS_KEY.format(project_id), "error")
            _push_log(r, project_id, f"[preview] Dev server exited with code {exit_code}")
            publish("preview.failed", {"project_id": project_id, "error": f"exit code {exit_code}"})
            # Collect recent logs and create a build ticket
            log_lines = r.lrange(_LOG_KEY.format(project_id), -100, -1)
            error_log = "\n".join(l.decode() if isinstance(l, bytes) else l for l in log_lines)
            asyncio.run(_create_build_ticket(project_id, error_log))
        else:
            r.set(_STATUS_KEY.format(project_id), "stopped")


@celery_app.task(name="workers.preview_worker.start_preview")
def start_preview(project_id: str):
    workspace = Path(settings.workspace_base_path) / f"project-{project_id}" / "astro-site"
    r = _redis()

    if not workspace.exists():
        r.set(_STATUS_KEY.format(project_id), "error")
        _push_log(r, project_id, "[preview] Workspace not found. Run PM Agent first.")
        publish("preview.failed", {"project_id": project_id, "error": "Workspace not found"})
        return

    # Kill any existing preview
    _kill_existing(r, project_id)

    # Reset log list and status
    r.delete(_LOG_KEY.format(project_id))
    r.set(_STATUS_KEY.format(project_id), "installing")
    publish("preview.started", {"project_id": project_id})

    # --- install only if node_modules is missing or incomplete ---
    node_modules = workspace / "node_modules"
    astro_bin = node_modules / ".bin" / "astro"
    needs_install = not astro_bin.exists()

    if needs_install:
        # Wipe corrupt/partial install before retrying
        if node_modules.exists():
            _push_log(r, project_id, "[preview] Incomplete node_modules found — reinstalling…")
            import shutil
            shutil.rmtree(str(node_modules), ignore_errors=True)

        _push_log(r, project_id, "[preview] Running npm install…")
        install = subprocess.run(
            "npm install",
            shell=True,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if install.returncode != 0:
            r.set(_STATUS_KEY.format(project_id), "error")
            error_log = install.stdout + install.stderr
            for line in error_log.splitlines():
                _push_log(r, project_id, line)
            publish("preview.failed", {"project_id": project_id, "error": "npm install failed"})
            asyncio.run(_create_build_ticket(project_id, error_log))
            return
        _push_log(r, project_id, "[preview] npm install complete.")
    else:
        _push_log(r, project_id, "[preview] node_modules already installed — skipping npm install.")
    r.set(_STATUS_KEY.format(project_id), "starting")

    # --- start dev server ---
    _push_log(r, project_id, f"[preview] Starting Astro dev server on port {PREVIEW_PORT}…")
    proc = subprocess.Popen(
        ["npm", "run", "dev", "--", "--port", str(PREVIEW_PORT), "--host", "0.0.0.0", "--strictPort"],
        cwd=str(workspace),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
    )

    r.set(_PID_KEY.format(project_id), proc.pid)
    r.set(_PORT_KEY.format(project_id), PREVIEW_PORT)

    # Tail logs in a background thread so the Celery task can return
    t = threading.Thread(target=_tail_logs, args=(proc, project_id, r), daemon=True)
    t.start()


@celery_app.task(name="workers.preview_worker.stop_preview")
def stop_preview(project_id: str):
    r = _redis()
    _kill_existing(r, project_id)
    r.set(_STATUS_KEY.format(project_id), "stopped")
    publish("preview.stopped", {"project_id": project_id})
