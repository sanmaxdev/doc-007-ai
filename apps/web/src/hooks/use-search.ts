"use client";

import { useMutation } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useRetrieve(workspaceId: string | null) {
  return useMutation({
    mutationFn: (payload: {
      question: string;
      document_ids?: string[];
      top_k?: number;
      hybrid?: boolean;
    }) => api.retrieve(workspaceId as string, payload),
  });
}
