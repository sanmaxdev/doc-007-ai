"use client";

import { ArrowLeft, FileText } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { StatusBadge } from "@/components/documents/status-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useChunks, useDocument } from "@/hooks/use-documents";
import { useWorkspaceStore } from "@/stores/workspace";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function Meta({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </p>
      <p className={`mt-1 text-sm font-medium ${mono ? "font-mono tabular-nums" : ""}`}>
        {value}
      </p>
    </div>
  );
}

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const documentId = params.id;
  const workspaceId = useWorkspaceStore((s) => s.activeId);

  const { data: doc, isLoading } = useDocument(workspaceId, documentId);
  const { data: chunks } = useChunks(workspaceId, documentId);

  return (
    <div className="space-y-6">
      <Link
        href="/documents"
        className="inline-flex items-center gap-1 font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Documents
      </Link>

      {isLoading ? (
        <div className="space-y-6">
          <Skeleton className="h-9 w-72" />
          <Skeleton className="h-28 rounded-lg" />
          <Skeleton className="h-64 rounded-lg" />
        </div>
      ) : !doc ? (
        <Card className="p-12 text-center">
          <p className="text-sm text-muted-foreground">Document not found.</p>
        </Card>
      ) : (
        <>
          <div className="flex items-start gap-3">
            <span className="mt-0.5 grid h-11 w-11 shrink-0 place-items-center rounded-lg border border-border bg-secondary/60">
              <FileText className="h-5 w-5 text-muted-foreground" />
            </span>
            <div className="min-w-0">
              <h1 className="break-all font-display text-2xl font-bold tracking-tight">
                {doc.original_filename}
              </h1>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <StatusBadge status={doc.status} />
                {doc.tags.map((t) => (
                  <Badge key={t.id} variant="info">
                    {t.name}
                  </Badge>
                ))}
              </div>
            </div>
          </div>

          {doc.status === "failed" && doc.error_message && (
            <Card className="border-destructive/40 bg-destructive/5">
              <CardContent className="p-4 text-sm text-destructive">
                {doc.error_message}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardContent className="grid grid-cols-2 gap-5 p-5 sm:grid-cols-4">
              <Meta label="Status" value={doc.status} />
              <Meta
                label="Pages"
                value={doc.page_count != null ? String(doc.page_count) : "-"}
                mono
              />
              <Meta label="Chunks" value={String(doc.chunk_count)} mono />
              <Meta label="Size" value={formatBytes(doc.file_size_bytes)} mono />
              <Meta label="Type" value={doc.mime_type} mono />
              <Meta label="Uploaded" value={new Date(doc.created_at).toLocaleString()} mono />
              <Meta
                label="Processed"
                value={doc.processed_at ? new Date(doc.processed_at).toLocaleString() : "-"}
                mono
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Chunks
                <span className="font-mono text-sm font-normal tabular-nums text-muted-foreground">
                  {chunks?.length ?? 0}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {!chunks || chunks.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No chunks yet. Chunks appear once the document finishes processing.
                </p>
              ) : (
                chunks.map((c) => (
                  <div
                    key={c.id}
                    className="rounded-md border border-border bg-background/40 p-3"
                  >
                    <div className="mb-1.5 flex items-center gap-3 font-mono text-[11px] text-muted-foreground">
                      <span className="text-primary">#{c.chunk_index}</span>
                      {c.page_number != null && <span>page {c.page_number}</span>}
                      <span>{c.token_count} tokens</span>
                    </div>
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">{c.content}</p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
