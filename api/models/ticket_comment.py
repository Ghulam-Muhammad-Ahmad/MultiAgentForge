import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id: Mapped[str] = mapped_column(String, ForeignKey("tickets.id"), nullable=False)
    author_type: Mapped[str] = mapped_column(String, nullable=False)  # agent, user, system
    author_agent_id: Mapped[str | None] = mapped_column(String, ForeignKey("agents.id"), nullable=True)
    author_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String, default="public")  # public, internal, system
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    ticket = relationship("Ticket", back_populates="comments")
    author_agent = relationship("Agent", foreign_keys=[author_agent_id])
