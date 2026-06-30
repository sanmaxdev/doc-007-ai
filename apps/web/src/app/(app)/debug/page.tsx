"use client";

import { FlaskConical, Search } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useDocuments } from "@/hooks/use-documents";
import { useRetrieve } from "@/hooks/use-search";
import type { RetrievedChunk } from "@/lib/types";
import { useWorkspaceStore } from "@/stores/workspace";

function ScoreBar({ label, value, title }: { label: string; value: string; title?: string }) {
  return (
    <span
      title={title}
      className="inline-flex items-center gap-1 rounded bg-secondary px-1.5 py-0.5 text-xs"
    >
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium tabular-nums">{value}</span>
    </span>
  );
}

function ChunkRow({ chunk, rank }: { chunk: RetrievedChunk; rank: number }) {
  const [open, setOpen] = useState(false);
  const preview = chunk.content.length > 280 && !open
    ? `${chunk.content.slice(0, 280)}…`
    : chunk.content;
  return (
    <div className="rounded-md border border-border p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium">#{rank}</span>
        <span className="text-sm text-muted-foreground">{chunk.document_filename}</span>
        {chunk.page_number != null && (
          <span className="text-xs text-muted-foreground">p.{chunk.page_number}</span>
        )}
        <span className="text-xs text-muted-foreground">chunk {chunk.chunk_index}</span>
        <div className="ml-auto flex flex-wrap items-center gap-1">
          <ScoreBar label="fused" value={chunk.fused_score.toFixed(4)} title="RRF fused score" />
          <ScoreBar
            label="dense"
            value={chunk.score.toFixed(3)}
            title={chunk.dense_rank ? `vector rank #${chunk.dense_rank}` : "not in vector results"}
          />
          <ScoreBar
            label="lexical"
            value={chunk.lexical_score.toFixed(0)}
            title={chunk.lexical_rank ? `keyword rank #${chunk.lexical_rank}` : "no keyword match"}
          />
        </div>
      </div>
      <p className="whitespace-pre-wrap text-sm">{preview}</p>
      {chunk.content.length > 280 && (
        <button
          type="button"
          className="mt-1 text-xs text-primary hover:underline"
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
      <div className="flex items-center gap-2">
        <FlaskConical className="h-6 w-6 text-muted-foreground" />
        <div>
          <h1 className="text-2xl font-semibold">Retrieval debug</h1>
          <p className="text-sm text-muted-foreground">
            See exactly what the RAG pipeline retrieves and how it would be prompted. No
            answer is generated.
          </p>
        </div>
      </div>

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
              <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">
                Restrict to documents (optional)
              </p>
              <div className="flex flex-wrap gap-2">
                {docs.map((d) => (
                  <label
                    key={d.id}
                    className="flex cursor-pointer items-center gap-1.5 rounded-md border border-border px-2 py-1 text-xs"
                  >
                    <input
                      type="checkbox"
                      checked={selected.has(d.id)}
                      onChange={() => toggleDoc(d.id)}
                    />
                    {d.original_filename}
                  </label>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {result && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Badge variant="info">{result.method}</Badge>
            {result.not_found ? (
              <Badge variant="warning">below relevance threshold, would refuse</Badge>
            ) : (
              <Badge variant="success">{result.chunks.length} chunks retrieved</Badge>
            )}
          </div>

          {result.chunks.map((c, i) => (
            <ChunkRow key={c.chunk_id} chunk={c} rank={i + 1} />
          ))}

          <Card>
            <CardContent className="p-4">
              <button
                type="button"
                className="text-sm font-medium hover:underline"
                onClick={() => setShowPrompt((v) => !v)}
              >
                {showPrompt ? "Hide" : "Show"} assembled prompt
              </button>
              {showPrompt && (
                <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded bg-secondary/50 p-3 text-xs">
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
