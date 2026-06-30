"use client";

import { useQueryClient } from "@tanstack/react-query";
import { MessagesSquare, Plus, Send, ThumbsDown, ThumbsUp, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { CitationCard } from "@/components/chat/citation-card";
import { CoverageBadge } from "@/components/chat/coverage-badge";
import { Button } from "@/components/ui/button";
import {
  useConversation,
  useConversations,
  useDeleteConversation,
  useSubmitFeedback,
} from "@/hooks/use-chat";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ChatMessage, FeedbackRating } from "@/lib/types";
import { useWorkspaceStore } from "@/stores/workspace";

function MessageBubble({
  message,
  coverage,
  rating,
  streaming,
  onRate,
}: {
  message: ChatMessage;
  coverage?: string;
  rating?: FeedbackRating;
  streaming?: boolean;
  onRate?: (rating: FeedbackRating) => void;
}) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[82%] rounded-lg px-4 py-3 text-sm",
          isUser
            ? "rounded-br-sm bg-primary text-primary-foreground"
            : "rounded-bl-sm border border-border bg-secondary/50",
        )}
      >
        <p className="whitespace-pre-wrap leading-relaxed">
          {message.content}
          {streaming && (
            <span className="ml-0.5 inline-block h-4 w-1.5 -translate-y-px animate-pulse bg-primary align-middle" />
          )}
        </p>
        {!isUser && coverage && coverage !== "none" && (
          <div className="mt-2.5">
            <CoverageBadge coverage={coverage} />
          </div>
        )}
        {!isUser && message.citations.length > 0 && (
          <div className="mt-3 space-y-2">
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
              Sources
            </p>
            {message.citations.map((c) => (
              <CitationCard key={c.index} citation={c} />
            ))}
          </div>
        )}
        {!isUser && onRate && (
          <div className="mt-3 flex items-center gap-1 border-t border-border/60 pt-2.5">
            <span className="mr-1 text-xs text-muted-foreground">Was this helpful?</span>
            <button
              type="button"
              aria-label="Helpful"
              className={cn(
                "rounded p-1 transition-colors hover:bg-background",
                rating === "helpful" ? "text-accent" : "text-muted-foreground",
              )}
              onClick={() => onRate("helpful")}
            >
              <ThumbsUp className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              aria-label="Not helpful"
              className={cn(
                "rounded p-1 transition-colors hover:bg-background",
                rating === "not_helpful" ? "text-destructive" : "text-muted-foreground",
              )}
              onClick={() => onRate("not_helpful")}
            >
              <ThumbsDown className="h-3.5 w-3.5" />
            </button>
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

  const [feedbackByMsg, setFeedbackByMsg] = useState<Record<string, FeedbackRating>>({});
  const [pending, setPending] = useState<{ question: string; answer: string } | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const { data: conversations } = useConversations(workspaceId);
  const { data: detail } = useConversation(workspaceId, activeId);
  const del = useDeleteConversation(workspaceId);
  const feedback = useSubmitFeedback(workspaceId);

  async function rate(messageId: string, rating: FeedbackRating) {
    setFeedbackByMsg((prev) => ({ ...prev, [messageId]: rating }));
    try {
      await feedback.mutateAsync({ messageId, rating });
    } catch {
      setFeedbackByMsg((prev) => {
        const next = { ...prev };
        delete next[messageId];
        return next;
      });
    }
  }

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
    if (!q || streaming || !workspaceId) return;
    setQuestion("");
    setError(null);
    setPending({ question: q, answer: "" });
    setStreaming(true);
    await api.askStream(
      workspaceId,
      { question: q, conversation_id: activeId ?? undefined },
      {
        onToken: (t) => setPending((p) => (p ? { ...p, answer: p.answer + t } : p)),
        onDone: (d) => {
          setCoverageByMsg((prev) => ({ ...prev, [d.message_id]: d.coverage }));
          setActiveId(d.conversation_id);
          setPending(null);
          setStreaming(false);
          queryClient.invalidateQueries({ queryKey: ["conversations", workspaceId] });
          queryClient.invalidateQueries({
            queryKey: ["conversation", workspaceId, d.conversation_id],
          });
        },
        onError: (msg) => {
          setError(msg);
          setPending(null);
          setStreaming(false);
        },
      },
    );
  }

  const messages = detail?.messages ?? [];

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      <aside className="hidden w-60 shrink-0 flex-col rounded-lg border border-border bg-card md:flex">
        <div className="p-3">
          <Button variant="outline" className="w-full" onClick={() => setActiveId(null)}>
            <Plus className="h-4 w-4" />
            New chat
          </Button>
        </div>
        <p className="px-4 pb-1 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground/70">
          Conversations
        </p>
        <div className="flex-1 space-y-1 overflow-y-auto px-2 pb-2">
          {(conversations ?? []).length === 0 ? (
            <p className="px-2 py-3 text-xs text-muted-foreground">No conversations yet.</p>
          ) : (
            (conversations ?? []).map((c) => {
              const active = c.id === activeId;
              return (
                <div
                  key={c.id}
                  className={cn(
                    "group relative flex items-center gap-1 rounded-md px-2 py-2 text-sm transition-colors",
                    active ? "bg-secondary" : "hover:bg-secondary/60",
                  )}
                >
                  <span
                    className={cn(
                      "absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-primary transition-opacity",
                      active ? "opacity-100" : "opacity-0",
                    )}
                  />
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
              );
            })
          )}
        </div>
      </aside>

      <div className="flex flex-1 flex-col overflow-hidden rounded-lg border border-border bg-card">
        <div className="flex-1 space-y-6 overflow-y-auto p-6">
          {messages.length === 0 && !pending ? (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <span className="grid h-14 w-14 place-items-center rounded-2xl border border-border bg-secondary/60">
                <MessagesSquare className="h-6 w-6 text-primary" />
              </span>
              <p className="mt-4 font-display text-lg font-semibold">Ask your documents</p>
              <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                Answers are grounded in this workspace and cite the exact sources they came from.
              </p>
            </div>
          ) : (
            messages.map((m) => (
              <MessageBubble
                key={m.id}
                message={m}
                coverage={coverageByMsg[m.id]}
                rating={feedbackByMsg[m.id]}
                onRate={m.role === "assistant" ? (r) => rate(m.id, r) : undefined}
              />
            ))
          )}
          {pending && (
            <>
              <MessageBubble
                message={{
                  id: "pending-user",
                  role: "user",
                  content: pending.question,
                  created_at: "",
                  citations: [],
                }}
              />
              {pending.answer ? (
                <MessageBubble
                  streaming
                  message={{
                    id: "pending-assistant",
                    role: "assistant",
                    content: pending.answer,
                    created_at: "",
                    citations: [],
                  }}
                />
              ) : (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span className="flex gap-1">
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:-0.3s]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:-0.15s]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60" />
                  </span>
                  Retrieving and reasoning…
                </div>
              )}
            </>
          )}
          {error && (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}
        </div>

        <form onSubmit={submit} className="flex gap-2 border-t border-border p-4">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question about your documents…"
            className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <Button type="submit" disabled={streaming || !question.trim()}>
            <Send className="h-4 w-4" />
            Ask
          </Button>
        </form>
      </div>
    </div>
  );
}
