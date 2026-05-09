export interface Project {
  id: string;
  name: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Ticket {
  id: string;
  board_id: string;
  column_id: string;
  title: string;
  description: string;
  acceptance_criteria: string[];
  assigned_agent_id: string | null;
  agent_role: string;
  status: string;
  priority: "low" | "medium" | "high";
  files_affected: string[];
  dependencies: string[];
  created_at: string;
  updated_at: string;
}

export interface Column {
  id: string;
  board_id: string;
  name: string;
  position: number;
  tickets: Ticket[];
}

export interface Board {
  id: string;
  project_id: string;
  name: string;
  columns: Column[];
}

export interface Agent {
  id: string;
  project_id: string;
  name: string;
  role: string;
  status: "idle" | "running" | "waiting" | "error";
  created_at: string;
}

export interface Comment {
  id: string;
  ticket_id: string;
  author_type: "agent" | "user" | "system";
  author_agent_id: string | null;
  comment: string;
  visibility: string;
  created_at: string;
}

export interface RequirementDocument {
  id: string;
  project_id: string;
  source_type: string;
  raw_content: string;
  parsed_content: string;
  summary: string;
  created_at: string;
}

export interface AgentRun {
  id: string;
  ticket_id: string;
  agent_id: string;
  status: "queued" | "running" | "waiting_for_approval" | "completed" | "failed" | "cancelled";
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface DeliveryReport {
  project_id: string;
  project_name: string;
  project_status: string;
  tickets_total: number;
  tickets_done: number;
  tickets_by_status: Record<string, number>;
  files_tracked: number;
  file_list: string[];
  requirement_summary: string | null;
  workspace_exists: boolean;
}

export interface PreviewStatus {
  status: "stopped" | "installing" | "starting" | "running" | "error";
  port: number | null;
}

export interface CommandExecution {
  id: string;
  project_id: string;
  ticket_id: string | null;
  command: string;
  classification: "safe" | "approval_required" | "blocked";
  status: string;
  requires_approval: boolean;
  stdout: string;
  stderr: string;
  exit_code: number | null;
  created_at: string;
}
