"use client";

import { ArrowLeft, FileText } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { StatusBadge } from "@/components/documents/status-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useChunks, useDocument } from "@/hooks/use-documents";
import { useWorkspaceStore } from "@/stores/workspace";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-sm font-medium">{value}</p>
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
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Documents
      </Link>

      {isLoading ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : !doc ? (
        <p className="text-muted-foreground">Document not found.</p>
      ) : (
        <>
          <div className="flex items-start gap-3">
            <FileText className="mt-1 h-6 w-6 shrink-0 text-muted-foreground" />
            <div>
              <h1 className="text-2xl font-semibold">{doc.original_filename}</h1>
              <div className="mt-1 flex items-center gap-2">
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
            <Card className="border-destructive/40">
              <CardContent className="p-4 text-sm text-destructive">
                {doc.error_message}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardContent className="grid grid-cols-2 gap-4 p-5 sm:grid-cols-4">
              <Meta label="Status" value={doc.status} />
              <Meta label="Pages" value={doc.page_count != null ? String(doc.page_count) : "-"} />
              <Meta label="Chunks" value={String(doc.chunk_count)} />
              <Meta label="Size" value={formatBytes(doc.file_size_bytes)} />
              <Meta label="Type" value={doc.mime_type} />
              <Meta
                label="Uploaded"
                value={new Date(doc.created_at).toLocaleString()}
              />
              <Meta
                label="Processed"
                value={doc.processed_at ? new Date(doc.processed_at).toLocaleString() : "-"}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Chunks ({chunks?.length ?? 0})</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {!chunks || chunks.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No chunks yet. Chunks appear once the document finishes processing.
                </p>
              ) : (
                chunks.map((c) => (
                  <div key={c.id} className="rounded-md border border-border p-3">
                    <div className="mb-1 flex items-center gap-3 text-xs text-muted-foreground">
                      <span>#{c.chunk_index}</span>
                      {c.page_number != null && <span>page {c.page_number}</span>}
                      <span>{c.token_count} tokens</span>
                    </div>
                    <p className="whitespace-pre-wrap text-sm">{c.content}</p>
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
