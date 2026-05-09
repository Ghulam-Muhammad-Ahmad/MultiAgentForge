"""Base agent class — agentic tool-use loop over OpenAI."""
import hashlib
import json
import shutil
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import Agent, AgentRun, Ticket, TicketComment, ProjectFile, CommandExecution
from workers.event_bus import publish
from agents.command_runner import (
    classify,
    run_subprocess,
    wait_for_approval,
    safe_path,
    SIGNAL_KEY_PREFIX,
)

MAX_ITERATIONS = 20

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Create or overwrite a file in the Astro project workspace. "
                "path is relative to the astro-site root, e.g. 'src/pages/index.astro'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the contents of an existing file in the Astro project workspace. "
                "path is relative to the astro-site root."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Execute a shell command in the project workspace. "
                "Safe commands run immediately. Others require user approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_comment",
            "description": "Post a progress update or summary comment on the ticket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "comment": {"type": "string"},
                },
                "required": ["comment"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": (
                "Create a new Kanban ticket for work that needs to be done. "
                "Use this when you find a missing feature, broken file, or failed build "
                "that requires another agent to fix. The ticket goes into the Ready column."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short imperative title."},
                    "description": {"type": "string", "description": "What needs to be done and why."},
                    "agent_role": {
                        "type": "string",
                        "enum": ["frontend", "seo", "backend", "qa", "build", "copy", "design_review"],
                        "description": "Which agent should handle this.",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "default": "high",
                    },
                    "acceptance_criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "2-4 specific testable pass/fail criteria.",
                    },
                },
                "required": ["title", "description", "agent_role", "priority", "acceptance_criteria"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "handoff_ticket",
            "description": (
                "Reassign this ticket to a different agent when the task is outside your domain. "
                "Use this when: the file type belongs to another agent, the work requires skills "
                "you do not have, or you were assigned by mistake. "
                "The ticket will be reassigned and re-queued for the correct agent immediately."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_role": {
                        "type": "string",
                        "enum": ["frontend", "seo", "backend", "qa", "build"],
                        "description": "Role of the agent that should handle this ticket.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why this ticket does not belong to you.",
                    },
                },
                "required": ["agent_role", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Replace an exact string in an existing file. "
                "Use this for targeted fixes instead of rewriting the whole file. "
                "old_string must match the file content exactly (including whitespace). "
                "Fails if old_string is not found."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file."},
                    "old_string": {"type": "string", "description": "Exact string to replace."},
                    "new_string": {"type": "string", "description": "String to replace it with."},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_ticket_outcome",
            "description": (
                "Finalize the ticket outcome. Use 'done' if all acceptance criteria pass, "
                "'changes_requested' if issues were found that need fixing. "
                "Always call this as your last action."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "outcome": {
                        "type": "string",
                        "enum": ["done", "changes_requested"],
                    },
                    "summary": {
                        "type": "string",
                        "description": "Brief explanation of the outcome.",
                    },
                },
                "required": ["outcome", "summary"],
            },
        },
    },
]


class BaseAgent(ABC):
    role: str
    model: str = "gpt-4.1"

    @property
    @abstractmethod
    def system_prompt(self) -> str: ...

    async def execute(
        self,
        db: AsyncSession,
        ticket_id: str,
        agent_id: str,
    ) -> None:
        # Load data
        ticket = await _get_ticket(db, ticket_id)
        agent = await _get_agent(db, agent_id)
        if not ticket or not agent:
            publish("agent.run.failed", {"agent_id": agent_id, "ticket_id": ticket_id, "error": "Not found"})
            return

        from models import Board
        board_result = await db.execute(select(Board).where(Board.id == ticket.board_id))
        board = board_result.scalar_one_or_none()
        project_id = board.project_id if board else ""

        workspace = str(Path(settings.workspace_base_path) / f"project-{project_id}" / "astro-site")

        # Create AgentRun
        run = AgentRun(
            id=str(uuid.uuid4()),
            ticket_id=ticket_id,
            agent_id=agent_id,
            status="running",
            input_payload={"ticket_title": ticket.title},
            started_at=datetime.utcnow(),
        )
        db.add(run)

        # Move ticket to In Progress
        ip_col = await _get_column_by_name(db, ticket.board_id, "In Progress")
        if ip_col:
            ticket.column_id = ip_col.id
            ticket.status = "in_progress"

        agent.status = "running"
        await db.commit()

        publish("agent.run.started", {
            "agent_id": agent_id,
            "ticket_id": ticket_id,
            "role": self.role,
        })
        publish("ticket.updated", {"ticket_id": ticket_id, "column_id": ticket.column_id})

        # Build context
        existing_files = await _list_workspace_files(db, project_id)
        user_message = self._build_context(ticket, existing_files)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]

        # Agentic loop
        client = AsyncOpenAI(api_key=settings.openai_api_key, max_retries=6, timeout=120.0)
        iteration = 0
        files_written: list[str] = []
        files_edited: list[str] = []
        error: str | None = None
        ticket_outcome: str | None = None  # set by set_ticket_outcome tool
        command_failed = False

        try:
            while iteration < MAX_ITERATIONS:
                # Check for cancellation before each iteration
                await db.refresh(run)
                if run.status == "cancelled":
                    ticket_outcome = "cancelled"
                    break

                iteration += 1
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                )
                msg: ChatCompletionMessage = response.choices[0].message
                messages.append(msg.model_dump(exclude_none=True))

                if not msg.tool_calls:
                    break  # Agent is done

                tool_results = []
                outcome_set_this_turn = False
                for tc in msg.tool_calls:
                    fn = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}

                    if fn == "write_file":
                        result_text = await self._handle_write_file(
                            db, args, workspace, project_id, agent_id, ticket_id, files_written
                        )
                    elif fn == "read_file":
                        result_text = await self._handle_read_file(args, workspace)
                    elif fn == "edit_file":
                        result_text = await self._handle_edit_file(args, workspace, files_edited)
                    elif fn == "run_command":
                        result_text = await self._handle_run_command(
                            db, args, workspace, project_id, agent_id, ticket_id
                        )
                        if _command_result_failed(result_text):
                            command_failed = True
                        elif args.get("command", "").strip() == "npm run build":
                            command_failed = False  # successful build clears earlier failed attempt
                    elif fn == "add_comment":
                        result_text = await self._handle_add_comment(
                            db, args, ticket_id, agent_id
                        )
                    elif fn == "create_ticket":
                        result_text = await self._handle_create_ticket(
                            db, args, ticket.board_id, agent_id
                        )
                    elif fn == "handoff_ticket":
                        result_text = await self._handle_handoff_ticket(
                            db, args, ticket_id, agent_id, ticket.board_id
                        )
                        ticket_outcome = "handoff"
                        outcome_set_this_turn = True
                    elif fn == "set_ticket_outcome":
                        if command_failed and args.get("outcome") == "done":
                            args = dict(args)
                            args["outcome"] = "changes_requested"
                            args["summary"] = (
                                "A previous command failed, so this ticket cannot be marked Done. "
                                + args.get("summary", "")
                            ).strip()
                        result_text = await self._handle_set_ticket_outcome(
                            db, args, ticket_id, agent_id
                        )
                        ticket_outcome = args.get("outcome")
                        outcome_set_this_turn = True
                    else:
                        result_text = f"Unknown tool: {fn}"

                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_text,
                    })

                await db.commit()
                messages.extend(tool_results)

                if outcome_set_this_turn:
                    break  # Outcome is final — no further iterations needed

        except Exception as exc:
            error = str(exc)

        # Finalize
        if error:
            run.status = "failed"
            run.error_message = error
            agent.status = "error"
            ticket.status = "error"
            publish("agent.run.failed", {"agent_id": agent_id, "ticket_id": ticket_id, "error": error})
        else:
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.output_payload = {"files_written": files_written, "files_edited": files_edited, "outcome": ticket_outcome}
            agent.status = "idle"

            if ticket_outcome == "done":
                done_col = await _get_column_by_name(db, ticket.board_id, "Done")
                if done_col:
                    ticket.column_id = done_col.id
                    ticket.status = "done"
            elif ticket_outcome == "changes_requested":
                cr_col = await _get_column_by_name(db, ticket.board_id, "Changes Requested")
                if cr_col:
                    ticket.column_id = cr_col.id
                    ticket.status = "changes_requested"
            elif ticket_outcome == "handoff":
                pass  # ticket already reassigned and re-queued in handler
            elif ticket_outcome == "cancelled":
                pass  # cancel endpoint already updated ticket/agent status
            else:
                # Default: move to Review for human/QA inspection
                review_col = await _get_column_by_name(db, ticket.board_id, "Review")
                if review_col:
                    ticket.column_id = review_col.id
                    ticket.status = "review"

            publish("agent.run.completed", {
                "agent_id": agent_id,
                "ticket_id": ticket_id,
                "role": self.role,
                "files_written": files_written,
                "outcome": ticket_outcome,
            })
            publish("ticket.updated", {"ticket_id": ticket_id, "column_id": ticket.column_id})

        await db.commit()

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    async def _handle_write_file(
        self, db, args, workspace, project_id, agent_id, ticket_id, files_written
    ) -> str:
        path = args.get("path", "")
        content = args.get("content", "")
        if not path:
            return "Error: path required"
        try:
            target = safe_path(workspace, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            files_written.append(path)

            # Track in DB
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            existing = await db.execute(
                select(ProjectFile).where(
                    ProjectFile.project_id == project_id,
                    ProjectFile.path == path,
                )
            )
            pf = existing.scalar_one_or_none()
            if pf:
                pf.content_hash = content_hash
                pf.last_modified_by_agent_id = agent_id
            else:
                db.add(ProjectFile(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    path=path,
                    content_hash=content_hash,
                    last_modified_by_agent_id=agent_id,
                ))

            publish("file.written", {"project_id": project_id, "path": path, "agent_id": agent_id})
            return f"Written: {path}"
        except ValueError as e:
            return f"Blocked: {e}"
        except Exception as e:
            return f"Error writing file: {e}"

    async def _handle_run_command(
        self, db, args, workspace, project_id, agent_id, ticket_id
    ) -> str:
        command = args.get("command", "").strip()
        if not command:
            return "Error: command required"

        classification = classify(command)
        cmd_id = str(uuid.uuid4())

        cmd = CommandExecution(
            id=cmd_id,
            project_id=project_id,
            ticket_id=ticket_id,
            agent_id=agent_id,
            command=command,
            working_directory=workspace,
            classification=classification,
            status="pending",
            requires_approval=(classification == "approval_required"),
        )
        db.add(cmd)
        await db.commit()

        if classification == "blocked":
            cmd.status = "blocked"
            await db.commit()
            publish("command.blocked", {"command_id": cmd_id, "command": command})
            return f"Blocked: command not permitted — {command}"

        if classification == "approval_required":
            cmd.status = "pending"
            await db.commit()
            publish("command.requested", {
                "command_id": cmd_id,
                "command": command,
                "project_id": project_id,
                "ticket_id": ticket_id,
                "classification": classification,
            })

            signal = await wait_for_approval(cmd_id)
            if signal != "approved":
                cmd.status = "rejected"
                await db.commit()
                return f"Command rejected by user: {command}"

        pre_stdout = ""
        pre_stderr = ""
        if command.startswith("npm run "):
            pre_stdout, pre_stderr, pre_exit_code = self._ensure_npm_dependencies(workspace)
            if pre_exit_code != 0:
                cmd.stdout = pre_stdout[:4000]
                cmd.stderr = pre_stderr[:2000]
                cmd.exit_code = pre_exit_code
                cmd.status = "completed"
                cmd.completed_at = datetime.utcnow()
                await db.commit()
                publish("command.completed", {"command_id": cmd_id, "exit_code": pre_exit_code})
                return f"exit={pre_exit_code}\n{pre_stdout.strip()}\n{pre_stderr.strip()}".strip()

        # Execute
        stdout, stderr, exit_code = run_subprocess(command, workspace)
        combined_stdout = pre_stdout + stdout
        combined_stderr = pre_stderr + stderr
        cmd.stdout = combined_stdout[:4000]
        cmd.stderr = combined_stderr[:2000]
        cmd.exit_code = exit_code
        cmd.status = "completed"
        cmd.completed_at = datetime.utcnow()
        await db.commit()

        publish("command.completed", {"command_id": cmd_id, "exit_code": exit_code})
        output = combined_stdout.strip()[-2000:] if combined_stdout.strip() else ""
        err_text = combined_stderr.strip()
        # Keep start of stderr (where error location is) + tail (summary), drop middle stack trace
        if len(err_text) > 2000:
            err = err_text[:1500] + "\n...(truncated)...\n" + err_text[-300:]
        else:
            err = err_text
        return f"exit={exit_code}\n{output}\n{err}".strip()

    def _ensure_npm_dependencies(self, workspace: str) -> tuple[str, str, int]:
        root = Path(workspace)
        package_json = root / "package.json"
        node_modules = root / "node_modules"
        astro_bin = node_modules / ".bin" / "astro"

        if not package_json.exists() or astro_bin.exists():
            return "", "", 0

        if node_modules.exists():
            shutil.rmtree(str(node_modules), ignore_errors=True)

        stdout, stderr, exit_code = run_subprocess("npm install", workspace)
        return f"[dependencies] npm install\n{stdout}", stderr, exit_code

    async def _handle_edit_file(self, args: dict, workspace: str, files_edited: list[str] | None = None) -> str:
        path = args.get("path", "")
        old_string = args.get("old_string", "")
        new_string = args.get("new_string", "")
        if not path or old_string == "":
            return "Error: path and old_string required"
        try:
            target = safe_path(workspace, path)
            if not target.exists():
                return f"File not found: {path}"
            content = target.read_text(encoding="utf-8")
            if old_string not in content:
                return f"Error: old_string not found in {path}"
            updated = content.replace(old_string, new_string, 1)
            target.write_text(updated, encoding="utf-8")
            if files_edited is not None and path not in files_edited:
                files_edited.append(path)
            return f"Edited: {path}"
        except ValueError as e:
            return f"Blocked: {e}"
        except Exception as e:
            return f"Error editing file: {e}"

    async def _handle_read_file(self, args: dict, workspace: str) -> str:
        path = args.get("path", "")
        if not path:
            return "Error: path required"
        try:
            target = safe_path(workspace, path)
            if not target.exists():
                return f"File not found: {path}"
            content = target.read_text(encoding="utf-8")
            # Truncate very large files to avoid blowing context
            if len(content) > 8000:
                content = content[:8000] + "\n... (truncated)"
            return content
        except ValueError as e:
            return f"Blocked: {e}"
        except Exception as e:
            return f"Error reading file: {e}"

    async def _handle_set_ticket_outcome(self, db, args: dict, ticket_id: str, agent_id: str) -> str:
        outcome = args.get("outcome", "")
        summary = args.get("summary", "")
        if outcome not in ("done", "changes_requested"):
            return "Error: outcome must be 'done' or 'changes_requested'"
        # Post the summary as a public comment
        db.add(TicketComment(
            id=str(uuid.uuid4()),
            ticket_id=ticket_id,
            author_type="agent",
            author_agent_id=agent_id,
            comment=f"**QA Outcome: {outcome.replace('_', ' ').title()}**\n\n{summary}",
            visibility="public",
        ))
        await db.commit()
        publish("ticket.comment.created", {"ticket_id": ticket_id})
        return f"Outcome recorded: {outcome}"

    async def _handle_add_comment(self, db, args, ticket_id, agent_id) -> str:
        comment_text = args.get("comment", "")
        if not comment_text:
            return "Error: comment required"
        db.add(TicketComment(
            id=str(uuid.uuid4()),
            ticket_id=ticket_id,
            author_type="agent",
            author_agent_id=agent_id,
            comment=comment_text,
            visibility="public",
        ))
        await db.commit()
        publish("ticket.comment.created", {"ticket_id": ticket_id})
        return "Comment posted"

    async def _handle_handoff_ticket(
        self, db, args: dict, ticket_id: str, agent_id: str, board_id: str
    ) -> str:
        new_role = args.get("agent_role", "")
        reason = args.get("reason", "")
        if not new_role:
            return "Error: agent_role required"

        from models import Board, Agent as AgentModel
        board_result = await db.execute(select(Board).where(Board.id == board_id))
        board = board_result.scalar_one_or_none()
        if not board:
            return "Error: board not found"

        agent_result = await db.execute(
            select(AgentModel).where(
                AgentModel.project_id == board.project_id,
                AgentModel.role == new_role,
            )
        )
        target_agent = agent_result.scalar_one_or_none()
        if not target_agent:
            return f"Error: no agent with role '{new_role}' in project"

        ticket_result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
        ticket = ticket_result.scalar_one_or_none()
        if not ticket:
            return "Error: ticket not found"

        ticket.assigned_agent_id = target_agent.id
        ticket.agent_role = new_role
        ticket.status = "ready"

        ready_col = await _get_column_by_name(db, board_id, "Ready")
        if ready_col:
            ticket.column_id = ready_col.id

        db.add(TicketComment(
            id=str(uuid.uuid4()),
            ticket_id=ticket_id,
            author_type="agent",
            author_agent_id=agent_id,
            comment=f"**Handoff → {new_role}**\n\n{reason}",
            visibility="public",
        ))

        await db.commit()

        publish("ticket.handoff", {
            "ticket_id": ticket_id,
            "from_role": self.role,
            "to_role": new_role,
            "reason": reason,
        })
        publish("ticket.updated", {"ticket_id": ticket_id, "column_id": ticket.column_id})

        from workers.celery_app import celery_app
        celery_app.send_task(
            "workers.orchestrator.run_agent",
            args=[target_agent.id, ticket_id],
        )

        return f"Ticket handed off to {new_role} agent. Reason: {reason}"

    async def _handle_create_ticket(self, db, args: dict, board_id: str, agent_id: str) -> str:
        title = args.get("title", "").strip()
        description = args.get("description", "").strip()
        agent_role = args.get("agent_role", "frontend")
        priority = args.get("priority", "high")
        acceptance_criteria = args.get("acceptance_criteria", [])
        if not title:
            return "Error: title required"

        ready_col = await _get_column_by_name(db, board_id, "Ready")
        if not ready_col:
            ready_col = await _get_column_by_name(db, board_id, "Backlog")
        if not ready_col:
            return "Error: could not find Ready or Backlog column"

        from models import Agent as AgentModel
        agent_result = await db.execute(
            select(AgentModel).where(
                AgentModel.project_id == (
                    select(AgentModel.project_id).where(AgentModel.id == agent_id).scalar_subquery()
                ),
                AgentModel.role == agent_role,
            )
        )
        assigned_agent = agent_result.scalar_one_or_none()

        ticket = Ticket(
            id=str(uuid.uuid4()),
            board_id=board_id,
            column_id=ready_col.id,
            title=title,
            description=description,
            acceptance_criteria=acceptance_criteria,
            assigned_agent_id=assigned_agent.id if assigned_agent else None,
            agent_role=agent_role,
            status="ready",
            priority=priority,
            files_affected=[],
            dependencies=[],
            created_by_agent_id=agent_id,
        )
        db.add(ticket)
        await db.commit()

        publish("ticket.created", {
            "ticket_id": ticket.id,
            "board_id": board_id,
            "title": title,
            "agent_role": agent_role,
        })

        # Auto-dispatch immediately if agent is assigned
        if assigned_agent:
            from workers.celery_app import celery_app
            celery_app.send_task(
                "workers.orchestrator.run_agent",
                args=[assigned_agent.id, ticket.id],
            )

        return f"Ticket created: '{title}' (id={ticket.id})"

    def _build_context(self, ticket, existing_files: list[str]) -> str:
        ac = "\n".join(f"- {c}" for c in (ticket.acceptance_criteria or []))
        files_hint = "\n".join(f"  {f}" for f in (ticket.files_affected or []))
        existing = "\n".join(f"  {f}" for f in existing_files[:40]) or "  (empty workspace)"
        return f"""## Ticket: {ticket.title}

### Description
{ticket.description or "(no description)"}

### Acceptance Criteria
{ac or "(none)"}

### Expected Files
{files_hint or "(see description)"}

### Current Workspace Files
{existing}

---
Complete all acceptance criteria. Use write_file for every file you create or modify.
Use add_comment to post a final summary of what you completed.
"""


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def _get_ticket(db: AsyncSession, ticket_id: str):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    return result.scalar_one_or_none()


async def _get_agent(db: AsyncSession, agent_id: str):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    return result.scalar_one_or_none()


async def _get_column_by_name(db: AsyncSession, board_id: str, name: str):
    from models import Column
    result = await db.execute(
        select(Column).where(Column.board_id == board_id, Column.name == name)
    )
    return result.scalar_one_or_none()


async def _list_workspace_files(db: AsyncSession, project_id: str) -> list[str]:
    result = await db.execute(
        select(ProjectFile.path).where(ProjectFile.project_id == project_id)
    )
    return [r[0] for r in result.all()]


def _command_result_failed(result_text: str) -> bool:
    first_line = result_text.splitlines()[0] if result_text else ""
    if not first_line.startswith("exit="):
        return False
    try:
        return int(first_line.removeprefix("exit=")) != 0
    except ValueError:
        return True
