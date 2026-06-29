"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useWorkspaces() {
  return useQuery({ queryKey: ["workspaces"], queryFn: api.listWorkspaces });
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
