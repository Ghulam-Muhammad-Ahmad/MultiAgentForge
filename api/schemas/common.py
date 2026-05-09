from datetime import datetime
from pydantic import BaseModel


class ProjectBase(BaseModel):
    name: str
    description: str = ""


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class ProjectOut(ProjectBase):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RequirementCreate(BaseModel):
    raw_content: str
    source_type: str = "text"


class RequirementOut(BaseModel):
    id: str
    project_id: str
    source_type: str
    raw_content: str
    parsed_content: str
    summary: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketCreate(BaseModel):
    title: str
    description: str = ""
    acceptance_criteria: list[str] = []
    agent_role: str = ""
    priority: str = "medium"
    column_id: str


class TicketUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    acceptance_criteria: list[str] | None = None
    column_id: str | None = None
    assigned_agent_id: str | None = None
    status: str | None = None
    priority: str | None = None
    files_affected: list | None = None


class TicketOut(BaseModel):
    id: str
    board_id: str
    column_id: str
    title: str
    description: str
    acceptance_criteria: list[str]
    assigned_agent_id: str | None
    agent_role: str
    status: str
    priority: str
    files_affected: list
    dependencies: list
    created_by_agent_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CommentCreate(BaseModel):
    comment: str
    visibility: str = "public"


class CommentOut(BaseModel):
    id: str
    ticket_id: str
    author_type: str
    author_agent_id: str | None
    author_user_id: str | None
    comment: str
    visibility: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentOut(BaseModel):
    id: str
    project_id: str
    name: str
    role: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentRunOut(BaseModel):
    id: str
    ticket_id: str
    agent_id: str
    status: str
    input_payload: dict
    output_payload: dict
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CommandOut(BaseModel):
    id: str
    project_id: str
    ticket_id: str | None
    agent_id: str | None
    command: str
    classification: str
    status: str
    requires_approval: bool
    stdout: str
    stderr: str
    exit_code: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ColumnOut(BaseModel):
    id: str
    board_id: str
    name: str
    position: int
    tickets: list[TicketOut] = []

    model_config = {"from_attributes": True}


class BoardOut(BaseModel):
    id: str
    project_id: str
    name: str
    columns: list[ColumnOut] = []

    model_config = {"from_attributes": True}
