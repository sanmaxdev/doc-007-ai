"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { type DocumentItem, PROCESSING_STATUSES } from "@/lib/types";

export type DocumentFilters = {
  status_filter?: string;
  search?: string;
  tag_id?: string;
};

export function useDocuments(workspaceId: string | null, filters?: DocumentFilters) {
  return useQuery({
    queryKey: ["documents", workspaceId, filters ?? {}],
    queryFn: () => api.listDocuments(workspaceId as string, filters),
    enabled: Boolean(workspaceId),
    // Poll while anything is still being processed.
    refetchInterval: (query) => {
      const docs = query.state.data as DocumentItem[] | undefined;
      const processing = docs?.some((d) => PROCESSING_STATUSES.includes(d.status));
      return processing ? 2000 : false;
    },
  });
}

export function useDocument(workspaceId: string | null, documentId: string | null) {
  return useQuery({
    queryKey: ["document", workspaceId, documentId],
    queryFn: () => api.getDocument(workspaceId as string, documentId as string),
    enabled: Boolean(workspaceId && documentId),
  });
}

export function useChunks(workspaceId: string | null, documentId: string | null) {
  return useQuery({
    queryKey: ["chunks", workspaceId, documentId],
    queryFn: () => api.getChunks(workspaceId as string, documentId as string),
    enabled: Boolean(workspaceId && documentId),
  });
}

export function useTags(workspaceId: string | null) {
  return useQuery({
    queryKey: ["tags", workspaceId],
    queryFn: () => api.listTags(workspaceId as string),
    enabled: Boolean(workspaceId),
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

export function useAddTag(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ documentId, name }: { documentId: string; name: string }) =>
      api.addDocumentTag(workspaceId as string, documentId, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", workspaceId] });
      queryClient.invalidateQueries({ queryKey: ["tags", workspaceId] });
    },
  });
}

export function useRemoveTag(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ documentId, tagId }: { documentId: string; tagId: string }) =>
      api.removeDocumentTag(workspaceId as string, documentId, tagId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", workspaceId] });
      queryClient.invalidateQueries({ queryKey: ["tags", workspaceId] });
    },
  });
}
