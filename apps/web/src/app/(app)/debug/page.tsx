"use client";

import { Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PageHeader } from "@/components/app/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useDocuments } from "@/hooks/use-documents";
import { useRetrieve } from "@/hooks/use-search";
import { cn } from "@/lib/utils";
import type { RetrievedChunk } from "@/lib/types";
import { useWorkspaceStore } from "@/stores/workspace";

function ScoreChip({
  label,
  value,
  tone,
  title,
}: {
  label: string;
  value: string;
  tone: "primary" | "info" | "muted";
  title?: string;
}) {
  return (
    <span
      title={title}
      className="inline-flex items-center gap-1.5 rounded border border-border bg-background/60 px-1.5 py-0.5 font-mono text-[11px]"
    >
      <span
        className={cn(
          "uppercase tracking-wide",
          tone === "primary" && "text-primary",
          tone === "info" && "text-accent",
          tone === "muted" && "text-muted-foreground",
        )}
      >
        {label}
      </span>
      <span className="tabular-nums">{value}</span>
    </span>
  );
}

function ChunkRow({ chunk, rank }: { chunk: RetrievedChunk; rank: number }) {
  const [open, setOpen] = useState(false);
  const preview =
    chunk.content.length > 280 && !open ? `${chunk.content.slice(0, 280)}…` : chunk.content;
  return (
    <div className="rounded-lg border border-border bg-card p-3.5">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="font-mono text-sm font-semibold text-primary">#{rank}</span>
        <span className="text-sm font-medium">{chunk.document_filename}</span>
        {chunk.page_number != null && (
          <span className="font-mono text-xs text-muted-foreground">p.{chunk.page_number}</span>
        )}
        <span className="font-mono text-xs text-muted-foreground">chunk {chunk.chunk_index}</span>
        <div className="ml-auto flex flex-wrap items-center gap-1">
          <ScoreChip
            label="fused"
            tone="primary"
            value={chunk.fused_score.toFixed(4)}
            title="Reciprocal Rank Fusion score"
          />
          <ScoreChip
            label="dense"
            tone="info"
            value={chunk.score.toFixed(3)}
            title={chunk.dense_rank ? `vector rank #${chunk.dense_rank}` : "not in vector results"}
          />
          <ScoreChip
            label="lexical"
            tone="muted"
            value={chunk.lexical_score.toFixed(0)}
            title={chunk.lexical_rank ? `keyword rank #${chunk.lexical_rank}` : "no keyword match"}
          />
        </div>
      </div>
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
        {preview}
      </p>
      {chunk.content.length > 280 && (
        <button
          type="button"
          className="mt-1.5 font-mono text-xs text-primary hover:underline"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
}

export default function DebugPage() {
  const workspaceId = useWorkspaceStore((s) => s.activeId);
  const { data: docs } = useDocuments(workspaceId, { status_filter: "ready" });
  const retrieve = useRetrieve(workspaceId);

  const [question, setQuestion] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [showPrompt, setShowPrompt] = useState(false);

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

  function toggleDoc(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    retrieve.mutate({
      question: question.trim(),
      document_ids: selected.size ? Array.from(selected) : undefined,
    });
  }

  const result = retrieve.data;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Retrieval inspector"
        title="Retrieval debug"
        description="See exactly what the hybrid pipeline retrieves and how it would be prompted. No answer is generated, so it is safe to probe freely."
      />

      <Card>
        <CardContent className="space-y-4 p-5">
          <form onSubmit={run} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Test a question against your documents…"
                className="w-full rounded-md border border-input bg-background py-2 pl-9 pr-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </div>
            <Button type="submit" disabled={retrieve.isPending || !question.trim()}>
              {retrieve.isPending ? "Retrieving…" : "Retrieve"}
            </Button>
          </form>

          {docs && docs.length > 0 && (
            <div>
              <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                Restrict to documents (optional)
              </p>
              <div className="flex flex-wrap gap-2">
                {docs.map((d) => {
                  const on = selected.has(d.id);
                  return (
                    <label
                      key={d.id}
                      className={cn(
                        "flex cursor-pointer items-center gap-1.5 rounded-md border px-2 py-1 text-xs transition-colors",
                        on
                          ? "border-primary/40 bg-primary/10 text-foreground"
                          : "border-border hover:border-foreground/20",
                      )}
                    >
                      <input
                        type="checkbox"
                        className="accent-primary"
                        checked={on}
                        onChange={() => toggleDoc(d.id)}
                      />
                      {d.original_filename}
                    </label>
                  );
                })}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {result && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="info" className="font-mono uppercase tracking-wide">
              {result.method}
            </Badge>
            {result.not_found ? (
              <Badge variant="warning">Below relevance threshold, would refuse</Badge>
            ) : (
              <Badge variant="success">
                {result.chunks.length} chunk{result.chunks.length === 1 ? "" : "s"} retrieved
              </Badge>
            )}
          </div>

          {result.chunks.map((c, i) => (
            <ChunkRow key={c.chunk_id} chunk={c} rank={i + 1} />
          ))}

          <Card>
            <CardContent className="p-4">
              <button
                type="button"
                className="flex items-center gap-2 font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground transition-colors hover:text-foreground"
                onClick={() => setShowPrompt((v) => !v)}
              >
                {showPrompt ? "Hide" : "Show"} assembled prompt
              </button>
              {showPrompt && (
                <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded-md border border-border bg-background/60 p-3 font-mono text-xs leading-relaxed text-muted-foreground">
                  {result.prompt}
                </pre>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
