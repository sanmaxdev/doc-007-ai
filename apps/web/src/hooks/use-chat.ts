"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useConversations(workspaceId: string | null) {
  return useQuery({
    queryKey: ["conversations", workspaceId],
    queryFn: () => api.listConversations(workspaceId as string),
    enabled: Boolean(workspaceId),
  });
}

export function useConversation(workspaceId: string | null, conversationId: string | null) {
  return useQuery({
    queryKey: ["conversation", workspaceId, conversationId],
    queryFn: () => api.getConversation(workspaceId as string, conversationId as string),
    enabled: Boolean(workspaceId && conversationId),
  });
}

export function useAsk(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { question: string; conversation_id?: string }) =>
      api.ask(workspaceId as string, payload),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["conversations", workspaceId] });
      queryClient.invalidateQueries({
        queryKey: ["conversation", workspaceId, res.conversation_id],
      });
    },
  });
}

export function useDeleteConversation(workspaceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (conversationId: string) =>
      api.deleteConversation(workspaceId as string, conversationId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["conversations", workspaceId] }),
  });
}
