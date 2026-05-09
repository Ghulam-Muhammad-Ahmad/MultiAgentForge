import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id: Mapped[str] = mapped_column(String, ForeignKey("tickets.id"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, default="queued")  # queued, running, waiting_for_approval, completed, failed, cancelled
    input_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    ticket = relationship("Ticket", back_populates="agent_runs")
    agent = relationship("Agent", back_populates="runs")
