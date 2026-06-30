"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Role } from "@/lib/types";
import { useWorkspaceStore } from "@/stores/workspace";

export function useWorkspaces() {
  return useQuery({ queryKey: ["workspaces"], queryFn: api.listWorkspaces });
}

export function useActiveWorkspace() {
  const { data: workspaces } = useWorkspaces();
  const activeId = useWorkspaceStore((s) => s.activeId);
  return workspaces?.find((w) => w.id === activeId) ?? workspaces?.[0] ?? null;
}

export function useMembers(workspaceId: string | null) {
  return useQuery({
    queryKey: ["members", workspaceId],
    queryFn: () => api.listMembers(workspaceId as string),
    enabled: Boolean(workspaceId),
  });
}

export function useCreateWorkspace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ name, description }: { name: string; description?: string }) =>
      api.createWorkspace(name, description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workspaces"] });
    },
  });
}

export function useUpdateWorkspace(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { name?: string; description?: string }) =>
      api.updateWorkspace(workspaceId as string, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workspaces"] }),
  });
}

export function useDeleteWorkspace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (workspaceId: string) => api.deleteWorkspace(workspaceId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workspaces"] }),
  });
}

export function useChangeMemberRole(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: Role }) =>
      api.changeMemberRole(workspaceId as string, userId, role),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["members", workspaceId] }),
  });
}

export function useRemoveMember(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => api.removeMember(workspaceId as string, userId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["members", workspaceId] }),
  });
}

export function useInvitations(workspaceId: string | null, enabled = true) {
  return useQuery({
    queryKey: ["invitations", workspaceId],
    queryFn: () => api.listInvitations(workspaceId as string),
    enabled: Boolean(workspaceId) && enabled,
  });
}

export function useCreateInvitation(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ email, role }: { email: string; role: Role }) =>
      api.createInvitation(workspaceId as string, email, role),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["invitations", workspaceId] }),
  });
}

export function useRevokeInvitation(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (invitationId: string) =>
      api.revokeInvitation(workspaceId as string, invitationId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["invitations", workspaceId] }),
  });
}

export function useAcceptInvitation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (token: string) => api.acceptInvitation(token),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workspaces"] }),
  });
}

export function useAuditLogs(workspaceId: string | null, enabled = true) {
  return useQuery({
    queryKey: ["audit-logs", workspaceId],
    queryFn: () => api.listAuditLogs(workspaceId as string),
    enabled: Boolean(workspaceId) && enabled,
  });
}
