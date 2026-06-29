"use client";

import { Plus, Send, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { CitationCard } from "@/components/chat/citation-card";
import { CoverageBadge } from "@/components/chat/coverage-badge";
import { Button } from "@/components/ui/button";
import {
  useAsk,
  useConversation,
  useConversations,
  useDeleteConversation,
} from "@/hooks/use-chat";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/lib/types";
import { useWorkspaceStore } from "@/stores/workspace";

function MessageBubble({
  message,
  coverage,
}: {
  message: ChatMessage;
  coverage?: string;
}) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[80%] rounded-lg px-4 py-3 text-sm",
          isUser ? "bg-primary text-primary-foreground" : "bg-secondary",
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {!isUser && coverage && coverage !== "none" && (
          <div className="mt-2">
            <CoverageBadge coverage={coverage} />
          </div>
        )}
        {!isUser && message.citations.length > 0 && (
          <div className="mt-3 space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Sources</p>
            {message.citations.map((c) => (
              <CitationCard key={c.index} citation={c} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ChatPage() {
  const workspaceId = useWorkspaceStore((s) => s.activeId);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [coverageByMsg, setCoverageByMsg] = useState<Record<string, string>>({});

  const { data: conversations } = useConversations(workspaceId);
  const { data: detail } = useConversation(workspaceId, activeId);
  const ask = useAsk(workspaceId);
  const del = useDeleteConversation(workspaceId);

  if (!workspaceId) {
    return (
      <p className="text-muted-foreground">
        Select or create a workspace on the{" "}
        <Link href="/dashboard" className="text-primary underline-offset-4 hover:underline">
          dashboard
        </Link>{" "}
        first.
      </p>
    );
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || ask.isPending) return;
    setQuestion("");
    const res = await ask.mutateAsync({ question: q, conversation_id: activeId ?? undefined });
    setActiveId(res.conversation_id);
    setCoverageByMsg((prev) => ({ ...prev, [res.message_id]: res.coverage }));
  }

  const messages = detail?.messages ?? [];

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-4">
      <aside className="hidden w-60 shrink-0 flex-col rounded-lg border border-border bg-card md:flex">
        <div className="p-3">
          <Button variant="outline" className="w-full" onClick={() => setActiveId(null)}>
            <Plus className="h-4 w-4" />
            New chat
          </Button>
        </div>
        <div className="flex-1 space-y-1 overflow-y-auto px-2 pb-2">
          {(conversations ?? []).map((c) => (
            <div
              key={c.id}
              className={cn(
                "group flex items-center gap-1 rounded-md px-2 py-2 text-sm",
                c.id === activeId ? "bg-secondary" : "hover:bg-secondary",
              )}
            >
              <button
                type="button"
                className="flex-1 truncate text-left"
                onClick={() => setActiveId(c.id)}
              >
                {c.title || "Untitled"}
              </button>
              <button
                type="button"
                aria-label="Delete conversation"
                className="opacity-0 transition-opacity group-hover:opacity-100"
                onClick={() => {
                  del.mutate(c.id);
                  if (activeId === c.id) setActiveId(null);
                }}
              >
                <Trash2 className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
              </button>
            </div>
          ))}
        </div>
      </aside>

      <div className="flex flex-1 flex-col rounded-lg border border-border bg-card">
        <div className="flex-1 space-y-6 overflow-y-auto p-6">
          {messages.length === 0 && !ask.isPending ? (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <p className="text-lg font-medium">Ask your documents</p>
              <p className="text-sm text-muted-foreground">
                Answers are grounded in this workspace and include citations.
              </p>
            </div>
          ) : (
            messages.map((m) => (
              <MessageBubble key={m.id} message={m} coverage={coverageByMsg[m.id]} />
            ))
          )}
          {ask.isPending && <div className="text-sm text-muted-foreground">Thinking…</div>}
        </div>

        <form onSubmit={submit} className="flex gap-2 border-t border-border p-4">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question about your documents…"
            className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <Button type="submit" disabled={ask.isPending || !question.trim()}>
            <Send className="h-4 w-4" />
            Ask
          </Button>
        </form>
      </div>
    </div>
  );
}
