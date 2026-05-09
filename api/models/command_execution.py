import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Boolean, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class CommandExecution(Base):
    __tablename__ = "command_executions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), nullable=False)
    ticket_id: Mapped[str | None] = mapped_column(String, ForeignKey("tickets.id"), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String, ForeignKey("agents.id"), nullable=True)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    working_directory: Mapped[str] = mapped_column(String, default="")
    classification: Mapped[str] = mapped_column(String, nullable=False)  # safe, approval_required, blocked
    status: Mapped[str] = mapped_column(String, default="pending")  # pending, approved, rejected, completed, failed
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    stdout: Mapped[str] = mapped_column(Text, default="")
    stderr: Mapped[str] = mapped_column(Text, default="")
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    project = relationship("Project", back_populates="command_executions")
    ticket = relationship("Ticket", back_populates="command_executions")
    agent = relationship("Agent", foreign_keys=[agent_id])
