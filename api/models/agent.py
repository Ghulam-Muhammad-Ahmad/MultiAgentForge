import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)  # pm, frontend, seo, backend, qa
    status: Mapped[str] = mapped_column(String, default="idle")  # idle, running, waiting, error
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    memory_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="agents")
    runs = relationship("AgentRun", back_populates="agent", cascade="all, delete-orphan")
