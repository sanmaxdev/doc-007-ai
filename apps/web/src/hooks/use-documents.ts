"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { type DocumentItem, PROCESSING_STATUSES } from "@/lib/types";

export function useDocuments(workspaceId: string | null) {
  return useQuery({
    queryKey: ["documents", workspaceId],
    queryFn: () => api.listDocuments(workspaceId as string),
    enabled: Boolean(workspaceId),
    // Poll while anything is still being processed.
    refetchInterval: (query) => {
      const docs = query.state.data as DocumentItem[] | undefined;
      const processing = docs?.some((d) => PROCESSING_STATUSES.includes(d.status));
      return processing ? 2000 : false;
    },
  });
}

export function useUploadDocument(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => api.uploadDocument(workspaceId as string, file),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["documents", workspaceId] }),
  });
}

export function useDeleteDocument(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteDocument(workspaceId as string, id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["documents", workspaceId] }),
  });
}

export function useReprocessDocument(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.reprocessDocument(workspaceId as string, id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["documents", workspaceId] }),
  });
}
