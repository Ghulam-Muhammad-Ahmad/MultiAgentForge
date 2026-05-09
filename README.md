# MultiAgentForge

AI-powered website builder where a PM Agent converts requirement documents into Kanban tickets, and specialist agents collaborate to build and preview Astro websites.

## What It Does

1. User creates project and uploads requirements
2. System scaffolds Astro + TailwindCSS workspace
3. PM Agent analyzes requirements, creates Kanban tickets
4. Specialist agents execute: Frontend, SEO, Backend, QA
5. User reviews Astro preview

## Agent Team

| Agent | Role |
|-------|------|
| PM Agent | Parses requirements, creates tickets, assigns work, tracks progress |
| Frontend Agent | Builds Astro pages, components, layouts with TailwindCSS |
| SEO Agent | Metadata, headings, schema markup, page copy |
| Backend Agent | Astro API routes, form handlers, validation |
| QA Agent | Reviews acceptance criteria, runs build checks, approves/rejects tickets |

## Kanban Flow

```
Backlog → Ready → Assigned → In Progress → Waiting for Approval → Review → Changes Requested → Done → Presented to User
```

## Tech Stack

| Layer | Tech |
|-------|------|
| Dashboard | Next.js + React + TypeScript + TailwindCSS + shadcn/ui |
| UI State | Zustand |
| API State | React Query |
| Drag/Drop | dnd-kit |
| Backend API | FastAPI (Python) |
| Database | PostgreSQL |
| Task Queue | Celery + Redis |
| Realtime | WebSockets |
| Generated Sites | Astro + TailwindCSS |
| AI | OpenAI API |
| Structured Output | Pydantic + Instructor |

## Architecture

```
Next.js Dashboard
    ↓ REST + WebSocket
FastAPI Backend
    ↓
PM Agent (OpenAI) → Kanban tickets (PostgreSQL)
    ↓ Celery + Redis
Specialist Agents (Frontend / SEO / Backend / QA)
    ↓
Isolated Astro workspace (/workspaces/project-{id}/astro-site)
    ↓
Build → Preview → User approval
```

**Key constraint:** No direct agent-to-agent communication. Central orchestrator only.

## Command Permission Model

| Tier | Behavior | Examples |
|------|----------|---------|
| Safe | Auto-execute | `ls`, `cat`, `npm install`, `npm run build` |
| Approval Required | User must confirm | `rm`, `git push`, DB migrations, deploys |
| Blocked | Forbidden | `sudo`, system config, credential access |

## MVP Scope

- Single active project only
- No GitHub push, ZIP export, or production deployment
- Output: Astro preview served locally for user review

## Build Milestones

1. Foundation — auth, project creation, DB schema
2. Kanban Board — columns, tickets, drawer, comments
3. PM Agent — requirement parsing, ticket generation, agent assignment
4. Agent Execution — task queue, worker agents, run logs
5. Astro Workspace — scaffold, file write, file tracking
6. Command Permission Layer — classify, run, approve, log
7. QA + Preview — QA review, build, preview, delivery

## Docs

- [`PRD.md`](PRD.md) — Product requirements
- [`Spec-doc.md`](Spec-doc.md) — Technical specification
