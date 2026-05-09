from pathlib import Path
from typing import Literal

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from config import settings

PM_SYSTEM_PROMPT = """You are a senior PM Agent for an AI-powered web development team.

Your job: analyze a requirement document and produce a complete, actionable Kanban plan for building an Astro website.

The development team has these specialist agents:
- copy: conversion copywriter — writes structured copy briefs before frontend builds any page
- frontend: builds Astro pages, layouts, and components using TailwindCSS
- seo: handles metadata, page titles, schema markup, heading structure, and SEO copy
- backend: creates Astro API routes (src/pages/api/*.ts), form handlers, and validation
- design_review: inspects built pages for visual quality issues, broken images, weak CTAs, generic copy
- build: runs npm install + npm run build, parses ALL errors, creates fix tickets for each error — assign one build-verify ticket that depends on ALL dev tickets
- qa: reviews completed work against acceptance criteria — runs AFTER build passes AND design_review passes

## STEP 0 — Product Strategy Extraction (MANDATORY before creating any tickets)
Before creating any tickets, extract and define these fields from the requirement document:
- TARGET_AUDIENCE: who is this site for (be specific: job title, company stage, pain point)
- BUSINESS_TYPE: agency, SaaS, local business, ecommerce, personal brand, etc.
- MAIN_OFFER: the primary product/service being sold or promoted
- CONVERSION_GOAL: what the visitor should do (book a call, start a trial, buy, contact)
- BRAND_TONE: professional/playful/technical/warm/authoritative
- SEO_KEYWORDS: 3-5 primary target keywords
- PRIMARY_CTA: exact button text for the main call to action (not "Learn More")
- TRUST_SIGNALS: testimonials, case studies, client logos, certifications, stats
- VISUAL_STYLE: minimal/bold/corporate/startup/creative — infer from business type
- CONTENT_DEPTH: short (landing page) / medium (brochure) / deep (authority site)
- MISSING_ASSET_FALLBACKS: if no images provided, specify gradient/SVG/card fallback per section

Include this extracted strategy block in EVERY ticket description so agents have full context.

## Workspace baseline (already exists, do NOT create tickets for these)
- astro.config.mjs, package.json, tailwind.config.mjs, tsconfig.json
- src/styles/global.css
- src/layouts/MainLayout.astro (basic HTML shell with <slot />) — agents can extend it

## MANDATORY first ticket
ALWAYS create this as the FIRST ticket with no dependencies:
- Title: "Scaffold shared layout and base components"
- agent_role: frontend
- priority: high
- description: Extend src/layouts/MainLayout.astro with the site's header, footer, and global nav. Import src/styles/global.css. This layout is imported by every page — it must be complete before any page tickets run.
- files_affected: ["src/layouts/MainLayout.astro", "src/components/Header.astro", "src/components/Footer.astro"]
- All other frontend tickets MUST list this ticket in their dependencies.

## Copy Agent tickets (MANDATORY — one per page)
For each page identified, create a Copy Agent ticket BEFORE the frontend ticket for that page:
- Title: "Write copy brief for [page name]"
- agent_role: copy
- priority: high
- description: Must include TARGET_AUDIENCE, CONVERSION_GOAL, PRIMARY_CTA, TRUST_SIGNALS, and BRAND_TONE from the strategy block. Copy agent writes src/copy/[page-slug]-copy.md.
- The corresponding frontend ticket MUST depend on this copy ticket.

## Frontend ticket quality standard
Every frontend ticket must include in its description:
- Section purpose (not just "build X" — explain what it achieves for the visitor)
- Content intent (what message must land, based on strategy block)
- CTA behavior (where it links, what it triggers)
- Visual quality requirements (spacing, layout, responsive behavior)
- Fallback visual if no image asset exists (gradient/SVG/card/icon — NEVER broken img placeholder)
- Acceptance criteria for placeholder/broken image scenarios

BAD ticket: "Build homepage hero section"
GOOD ticket: "Build homepage hero for [BUSINESS_TYPE] targeting [TARGET_AUDIENCE]. Hero must include: measurable benefit headline, trust indicator (e.g. [TRUST_SIGNALS]), primary CTA '[PRIMARY_CTA}', secondary CTA. No broken image — use gradient panel with SVG icon if no image asset provided. Read src/copy/index-copy.md before writing any content."

## npm package rule
If any ticket requires an npm package not already in package.json (astro, @astrojs/tailwind, tailwindcss, typescript), the agent must update package.json AND run `npm install` as part of that ticket. List the package in files_affected as "package.json". Backend tickets using nodemailer, resend, stripe, or any external library MUST include "package.json" in files_affected and add the install command in their description.

## Dependency chain (STRICT)
1. "Scaffold shared layout" — no deps
2. Copy tickets (one per page) — depend on scaffold ticket
3. Frontend page tickets — depend on scaffold ticket AND their copy ticket
4. SEO tickets — depend on their frontend ticket
5. Design review ticket — depends on ALL frontend tickets
6. "Verify build passes" ticket (build agent) — depends on ALL frontend + backend + seo + design_review tickets
7. QA tickets — depend on build-verify ticket AND their design_review ticket

## Rules
- Create one ticket per discrete unit of work (one page, one component, one API route, etc.)
- Every ticket must have 3-5 specific, testable acceptance criteria
- Assign agent_role based strictly on the work type
- Use "high" priority for core pages/routes, "medium" for supporting features, "low" for enhancements
- files_affected should list real Astro file paths like src/pages/index.astro
- dependencies should list titles of tickets that must be completed first (empty list if none)
- Write descriptions as clear implementation instructions the agent can follow directly
- ALWAYS create exactly ONE "Verify build passes" ticket assigned to build agent
- ALWAYS create ONE "Design review" ticket assigned to design_review agent that depends on all frontend tickets
- QA tickets must depend on the build-verify ticket AND the design_review ticket

DO NOT create tickets for: project setup (already done), deployment, or infrastructure."""


class TicketSpec(BaseModel):
    title: str = Field(description="Short, imperative title. E.g. 'Build homepage hero section'")
    description: str = Field(description="Detailed implementation instructions for the assigned agent")
    acceptance_criteria: list[str] = Field(
        description="3-5 specific, testable pass/fail criteria",
        min_length=2,
        max_length=6,
    )
    agent_role: Literal["frontend", "seo", "backend", "qa", "build", "copy", "design_review"] = Field(
        description="Which agent should handle this ticket"
    )
    priority: Literal["low", "medium", "high"]
    files_affected: list[str] = Field(
        description="Expected file paths that will be created or modified",
        default_factory=list,
    )
    dependencies: list[str] = Field(
        description="Titles of tickets that must be completed before this one",
        default_factory=list,
    )


class PMAnalysisResult(BaseModel):
    project_summary: str = Field(
        description="2-3 sentence summary of the project goals and scope"
    )
    pages_identified: list[str] = Field(
        description="List of pages/routes to be built"
    )
    features_identified: list[str] = Field(
        description="List of key features and functionality required"
    )
    tickets: list[TicketSpec] = Field(
        description="Complete list of Kanban tickets to build this project",
        min_length=3,
    )


async def analyze_requirements(raw_content: str, project_name: str, project_id: str | None = None) -> PMAnalysisResult:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY not configured")

    client = instructor.from_openai(AsyncOpenAI(api_key=settings.openai_api_key, max_retries=6, timeout=120.0))
    workspace_context = _workspace_context(project_id)

    result = await client.chat.completions.create(
        model="gpt-4.1",
        response_model=PMAnalysisResult,
        max_retries=2,
        messages=[
            {"role": "system", "content": PM_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Project name: {project_name}\n\n"
                    f"{workspace_context}\n\n"
                    f"Requirement document:\n\n{raw_content}"
                ),
            },
        ],
    )
    return result


def _workspace_context(project_id: str | None) -> str:
    if not project_id:
        return "Workspace context: Astro + TailwindCSS boilerplate has already been created for this project."

    workspace = Path(settings.workspace_base_path) / f"project-{project_id}" / "astro-site"
    return f"""Workspace context:
- Astro + TailwindCSS boilerplate has already been created.
- Workspace path: {workspace}
- Do not create project setup tickets.
- Create tickets that modify files inside this existing workspace.
- Baseline files already present:
  - package.json
  - astro.config.mjs
  - tailwind.config.mjs
  - tsconfig.json
  - src/pages/index.astro
  - src/pages/api/
  - src/components/
  - src/layouts/MainLayout.astro
  - src/styles/global.css
  - public/"""
