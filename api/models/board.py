import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Board(Base):
    __tablename__ = "boards"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, default="Main Board")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project = relationship("Project", back_populates="boards")
    columns = relationship("Column", back_populates="board", cascade="all, delete-orphan", order_by="Column.position")
