export const PRIORITY_COLORS = {
  high: "error",
  medium: "warning",
  low: "muted",
} as const;

export const AGENT_ROLE_COLORS = {
  pm: "pm",
  frontend: "frontend",
  seo: "seo",
  backend: "backend",
  qa: "qa",
  build: "build",
} as const;

export const AGENT_ROLE_LABELS: Record<string, string> = {
  pm: "PM",
  frontend: "Frontend",
  seo: "SEO",
  backend: "Backend",
  qa: "QA",
  build: "Build",
};

export const COLUMN_COLORS: Record<string, string> = {
  "Backlog": "border-t-border",
  "Ready": "border-t-blue-500",
  "Assigned": "border-t-violet-500",
  "In Progress": "border-t-primary",
  "Waiting for Approval": "border-t-warning",
  "Review": "border-t-orange-500",
  "Changes Requested": "border-t-error",
  "Done": "border-t-success",
  "Presented to User": "border-t-emerald-400",
};
