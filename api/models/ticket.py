import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, ARRAY, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    board_id: Mapped[str] = mapped_column(String, ForeignKey("boards.id"), nullable=False)
    column_id: Mapped[str] = mapped_column(String, ForeignKey("columns.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    acceptance_criteria: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    assigned_agent_id: Mapped[str | None] = mapped_column(String, ForeignKey("agents.id"), nullable=True)
    agent_role: Mapped[str] = mapped_column(String, default="")  # denormalized
    status: Mapped[str] = mapped_column(String, default="backlog")
    priority: Mapped[str] = mapped_column(String, default="medium")  # low, medium, high
    files_affected: Mapped[dict] = mapped_column(JSONB, default=list)
    dependencies: Mapped[dict] = mapped_column(JSONB, default=list)
    created_by_agent_id: Mapped[str | None] = mapped_column(String, ForeignKey("agents.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    column = relationship("Column", back_populates="tickets")
    assigned_agent = relationship("Agent", foreign_keys=[assigned_agent_id])
    created_by_agent = relationship("Agent", foreign_keys=[created_by_agent_id])
    comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketComment.created_at")
    agent_runs = relationship("AgentRun", back_populates="ticket", cascade="all, delete-orphan")
    command_executions = relationship("CommandExecution", back_populates="ticket")
