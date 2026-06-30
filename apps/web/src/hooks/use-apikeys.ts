"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useApiKeys(workspaceId: string | null, enabled = true) {
  return useQuery({
    queryKey: ["api-keys", workspaceId],
    queryFn: () => api.listApiKeys(workspaceId as string),
    enabled: Boolean(workspaceId) && enabled,
  });
}

export function useCreateApiKey(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => api.createApiKey(workspaceId as string, name),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["api-keys", workspaceId] }),
  });
}

export function useRevokeApiKey(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) => api.revokeApiKey(workspaceId as string, keyId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["api-keys", workspaceId] }),
  });
}
