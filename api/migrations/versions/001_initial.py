"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("description", sa.String, server_default=""),
        sa.Column("status", sa.String, server_default="active"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "requirement_documents",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("project_id", sa.String, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("source_type", sa.String, server_default="text"),
        sa.Column("raw_content", sa.Text, nullable=False),
        sa.Column("parsed_content", sa.Text, server_default=""),
        sa.Column("summary", sa.Text, server_default=""),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "agents",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("project_id", sa.String, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("role", sa.String, nullable=False),
        sa.Column("status", sa.String, server_default="idle"),
        sa.Column("system_prompt", sa.Text, server_default=""),
        sa.Column("memory_config", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "boards",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("project_id", sa.String, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String, server_default="Main Board"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "columns",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("board_id", sa.String, sa.ForeignKey("boards.id"), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "tickets",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("board_id", sa.String, sa.ForeignKey("boards.id"), nullable=False),
        sa.Column("column_id", sa.String, sa.ForeignKey("columns.id"), nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("acceptance_criteria", ARRAY(sa.Text), server_default="{}"),
        sa.Column("assigned_agent_id", sa.String, sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("agent_role", sa.String, server_default=""),
        sa.Column("status", sa.String, server_default="backlog"),
        sa.Column("priority", sa.String, server_default="medium"),
        sa.Column("files_affected", JSONB, server_default="[]"),
        sa.Column("dependencies", JSONB, server_default="[]"),
        sa.Column("created_by_agent_id", sa.String, sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "ticket_comments",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("ticket_id", sa.String, sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("author_type", sa.String, nullable=False),
        sa.Column("author_agent_id", sa.String, sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("author_user_id", sa.String, nullable=True),
        sa.Column("comment", sa.Text, nullable=False),
        sa.Column("visibility", sa.String, server_default="public"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("ticket_id", sa.String, sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("agent_id", sa.String, sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("status", sa.String, server_default="queued"),
        sa.Column("input_payload", JSONB, server_default="{}"),
        sa.Column("output_payload", JSONB, server_default="{}"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "command_executions",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("project_id", sa.String, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("ticket_id", sa.String, sa.ForeignKey("tickets.id"), nullable=True),
        sa.Column("agent_id", sa.String, sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("command", sa.Text, nullable=False),
        sa.Column("working_directory", sa.String, server_default=""),
        sa.Column("classification", sa.String, nullable=False),
        sa.Column("status", sa.String, server_default="pending"),
        sa.Column("requires_approval", sa.Boolean, server_default="false"),
        sa.Column("approved_by_user_id", sa.String, nullable=True),
        sa.Column("stdout", sa.Text, server_default=""),
        sa.Column("stderr", sa.Text, server_default=""),
        sa.Column("exit_code", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "project_files",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("project_id", sa.String, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("path", sa.String, nullable=False),
        sa.Column("content_hash", sa.String, server_default=""),
        sa.Column("last_modified_by_agent_id", sa.String, sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("project_files")
    op.drop_table("command_executions")
    op.drop_table("agent_runs")
    op.drop_table("ticket_comments")
    op.drop_table("tickets")
    op.drop_table("columns")
    op.drop_table("boards")
    op.drop_table("agents")
    op.drop_table("requirement_documents")
    op.drop_table("projects")
