"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { useProjects } from "@/lib/api/hooks";
import type { Project } from "@/lib/api/types";

const STATUS_COLORS: Record<string, string> = {
  active: "bg-primary/15 text-primary border border-primary/30",
  delivered: "bg-success/15 text-success border border-success/30",
  archived: "bg-border/40 text-muted",
};

export default function HomePage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [content, setContent] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const { data: projects, isLoading } = useProjects();

  const createProject = useMutation({
    mutationFn: async () => {
      const project = await api.post<Project>("/projects", { name, description: "" });
      const rawContent = file ? await file.text() : content;
      await api.post(`/projects/${project.id}/requirements`, {
        raw_content: rawContent,
        source_type: file ? (file.name.endsWith(".md") ? "md" : "txt") : "text",
      });
      await api.post(`/projects/${project.id}/requirements/analyze`, {});
      return project;
    },
    onSuccess: (project) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      router.push(`/board?project_id=${project.id}`);
    },
  });

  const existingProjects = projects ?? [];

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-3xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Multi-Agent Builder</h1>
            <p className="text-muted text-sm mt-1">AI-powered Astro website development team.</p>
          </div>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="px-4 py-2 bg-primary hover:bg-primary/90 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {showForm ? "Cancel" : "+ New Project"}
          </button>
        </div>

        {/* Create form */}
        {showForm && (
          <div className="rounded-xl bg-card border border-border p-6 space-y-4">
            <h2 className="text-base font-semibold text-foreground">New Project</h2>

            <div>
              <label className="text-sm font-medium text-muted">Project name</label>
              <input
                className="mt-1 w-full rounded-lg bg-surface border border-border px-3 py-2 text-foreground focus:outline-none focus:border-primary text-sm"
                placeholder="My Astro Website"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />
            </div>

            <div>
              <label className="text-sm font-medium text-muted">Requirements</label>
              <textarea
                className="mt-1 w-full rounded-lg bg-surface border border-border px-3 py-2 text-foreground focus:outline-none focus:border-primary min-h-[160px] font-mono text-sm resize-y"
                placeholder="Describe the website you want to build…"
                value={content}
                onChange={(e) => setContent(e.target.value)}
              />
            </div>

            <div>
              <label className="text-sm font-medium text-muted">Or upload .txt / .md</label>
              <input
                type="file"
                accept=".txt,.md"
                className="mt-1 block text-sm text-muted"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </div>

            <button
              className="w-full bg-primary hover:bg-primary/90 text-white font-medium py-2 px-4 rounded-lg disabled:opacity-50 transition-colors text-sm flex items-center justify-center gap-2"
              disabled={!name || (!content && !file) || createProject.isPending}
              onClick={() => createProject.mutate()}
            >
              {createProject.isPending && (
                <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              )}
              {createProject.isPending ? "Creating project…" : "Create Project"}
            </button>

            {createProject.isError && (
              <p className="text-error text-sm">Failed to create project. Is the API running?</p>
            )}
          </div>
        )}

        {/* Project list */}
        <div className="space-y-3">
          {isLoading ? (
            <div className="rounded-xl bg-card border border-border p-8 text-center">
              <p className="text-muted text-sm">Loading projects…</p>
            </div>
          ) : existingProjects.length === 0 ? (
            <div className="rounded-xl bg-card border border-border p-10 text-center space-y-3">
              <p className="text-foreground font-medium">No projects yet</p>
              <p className="text-muted text-sm">Create your first project to get started.</p>
              {!showForm && (
                <button
                  onClick={() => setShowForm(true)}
                  className="mt-2 px-4 py-2 bg-primary hover:bg-primary/90 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  + New Project
                </button>
              )}
            </div>
          ) : (
            <>
              <p className="text-xs font-semibold text-muted uppercase tracking-wider">
                Projects ({existingProjects.length})
              </p>
              {existingProjects.map((project) => (
                <ProjectCard key={project.id} project={project} />
              ))}
            </>
          )}
        </div>
      </div>
    </main>
  );
}

function ProjectCard({ project }: { project: Project }) {
  const router = useRouter();

  return (
    <div className="rounded-xl bg-card border border-border p-4 flex items-center gap-4 hover:border-primary/40 transition-colors">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-foreground truncate">{project.name}</h3>
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${STATUS_COLORS[project.status] ?? STATUS_COLORS.active}`}
          >
            {project.status}
          </span>
        </div>
        <p className="text-xs text-muted mt-0.5">
          Created {new Date(project.created_at).toLocaleDateString()}
        </p>
      </div>

      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          onClick={() => router.push(`/activity?project_id=${project.id}`)}
          className="px-3 py-1.5 text-xs rounded-lg border border-border text-muted hover:text-foreground hover:border-primary/50 transition-colors"
        >
          Activity
        </button>
        <button
          onClick={() => router.push(`/delivery?project_id=${project.id}`)}
          className="px-3 py-1.5 text-xs rounded-lg border border-border text-muted hover:text-foreground hover:border-primary/50 transition-colors"
        >
          Delivery
        </button>
        <button
          onClick={() => router.push(`/board?project_id=${project.id}`)}
          className="px-3 py-1.5 text-xs rounded-lg bg-primary/15 border border-primary/30 text-primary hover:bg-primary/25 transition-colors font-medium"
        >
          Open Board →
        </button>
      </div>
    </div>
  );
}
