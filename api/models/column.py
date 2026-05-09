import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


COLUMN_NAMES = [
    "Backlog",
    "Ready",
    "Assigned",
    "In Progress",
    "Waiting for Approval",
    "Review",
    "Changes Requested",
    "Done",
    "Presented to User",
]


class Column(Base):
    __tablename__ = "columns"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    board_id: Mapped[str] = mapped_column(String, ForeignKey("boards.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    board = relationship("Board", back_populates="columns")
    tickets = relationship("Ticket", back_populates="column", order_by="Ticket.created_at")
