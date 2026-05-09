import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class RequirementDocument(Base):
    __tablename__ = "requirement_documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String, default="text")  # text, txt, md
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_content: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project = relationship("Project", back_populates="requirements")
