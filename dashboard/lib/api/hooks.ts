import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type { Project, Board, Ticket, Agent, Comment, RequirementDocument, CommandExecution, PreviewStatus, DeliveryReport, AgentRun } from "./types";

export function useProjects() {
  return useQuery<Project[]>({
    queryKey: ["projects"],
    queryFn: () => api.get("/projects"),
  });
}

export function useBoard(projectId: string) {
  return useQuery<Board>({
    queryKey: ["board", projectId],
    queryFn: () => api.get(`/projects/${projectId}/board`),
    enabled: !!projectId,
  });
}

export function useTicket(ticketId: string) {
  return useQuery<Ticket>({
    queryKey: ["ticket", ticketId],
    queryFn: () => api.get(`/tickets/${ticketId}`),
    enabled: !!ticketId,
  });
}

export function useTicketComments(ticketId: string) {
  return useQuery<Comment[]>({
    queryKey: ["ticket-comments", ticketId],
    queryFn: () => api.get(`/tickets/${ticketId}/comments`),
    enabled: !!ticketId,
  });
}

export function useAgents(projectId: string) {
  return useQuery<Agent[]>({
    queryKey: ["agents", projectId],
    queryFn: () => api.get(`/projects/${projectId}/agents`),
    enabled: !!projectId,
  });
}

export function useRequirements(projectId: string) {
  return useQuery<RequirementDocument[]>({
    queryKey: ["requirements", projectId],
    queryFn: () => api.get(`/projects/${projectId}/requirements`),
    enabled: !!projectId,
  });
}

export function useMoveTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ ticketId, columnId }: { ticketId: string; columnId: string }) =>
      api.patch(`/tickets/${ticketId}`, { column_id: columnId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["board"] }),
  });
}

export function useCreateTicket(boardId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      title: string;
      description?: string;
      acceptance_criteria?: string[];
      agent_role?: string;
      priority?: string;
      column_id: string;
    }) => api.post<Ticket>(`/boards/${boardId}/tickets`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["board"] }),
  });
}

export function useUpdateTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      ticketId,
      ...body
    }: {
      ticketId: string;
      title?: string;
      description?: string;
      acceptance_criteria?: string[];
      priority?: string;
      status?: string;
    }) => api.patch<Ticket>(`/tickets/${ticketId}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["board"] });
      qc.invalidateQueries({ queryKey: ["ticket"] });
    },
  });
}

export function useAddComment(ticketId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (comment: string) =>
      api.post<Comment>(`/tickets/${ticketId}/comments`, { comment, visibility: "public" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ticket-comments", ticketId] }),
  });
}

export function useAnalyzeRequirements(projectId: string) {
  return useMutation({
    mutationFn: () => api.post(`/projects/${projectId}/requirements/analyze`),
  });
}

export function useProjectCommands(projectId: string) {
  return useQuery<CommandExecution[]>({
    queryKey: ["commands", projectId],
    queryFn: () => api.get(`/projects/${projectId}/commands`),
    enabled: !!projectId,
    refetchInterval: 3000,
  });
}

export function useRunTicketAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ticketId: string) => api.post(`/tickets/${ticketId}/run`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["board"] }),
  });
}

export function useApproveCommand() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (commandId: string) => api.post(`/commands/${commandId}/approve`),
    onSuccess: (_, commandId) => qc.invalidateQueries({ queryKey: ["commands"] }),
  });
}

export function useRejectCommand() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (commandId: string) => api.post(`/commands/${commandId}/reject`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["commands"] }),
  });
}

export function useRetryRun(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => api.post(`/runs/${runId}/retry`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["runs", projectId] });
      qc.invalidateQueries({ queryKey: ["board"] });
      qc.invalidateQueries({ queryKey: ["agents", projectId] });
    },
  });
}

export function useCancelRun(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => api.post(`/runs/${runId}/cancel`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["runs", projectId] });
      qc.invalidateQueries({ queryKey: ["agents", projectId] });
      qc.invalidateQueries({ queryKey: ["board"] });
    },
  });
}

export function usePreviewStatus(projectId: string) {
  return useQuery<PreviewStatus>({
    queryKey: ["preview-status", projectId],
    queryFn: () => api.get(`/projects/${projectId}/preview/status`),
    enabled: !!projectId,
    refetchInterval: 2000,
  });
}

export function usePreviewLogs(projectId: string) {
  return useQuery<{ logs: string[] }>({
    queryKey: ["preview-logs", projectId],
    queryFn: () => api.get(`/projects/${projectId}/preview/logs`),
    enabled: !!projectId,
    refetchInterval: 2000,
  });
}

export function useStartPreview(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post(`/projects/${projectId}/preview/start`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["preview-status", projectId] });
      qc.invalidateQueries({ queryKey: ["preview-logs", projectId] });
    },
  });
}

export function useStopPreview(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post(`/projects/${projectId}/preview/stop`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["preview-status", projectId] }),
  });
}

export function useDeliveryReport(projectId: string) {
  return useQuery<DeliveryReport>({
    queryKey: ["delivery", projectId],
    queryFn: () => api.get(`/projects/${projectId}/delivery`),
    enabled: !!projectId,
    refetchInterval: 5000,
  });
}

export function useProjectRuns(projectId: string) {
  return useQuery<AgentRun[]>({
    queryKey: ["runs", projectId],
    queryFn: () => api.get(`/projects/${projectId}/runs`),
    enabled: !!projectId,
    refetchInterval: 4000,
  });
}

export function useMarkPresented(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post(`/projects/${projectId}/delivery/present`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["delivery", projectId] });
      qc.invalidateQueries({ queryKey: ["board", projectId] });
    },
  });
}
