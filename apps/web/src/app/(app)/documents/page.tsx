"use client";

import { FileText, Plus, RefreshCw, Search, Trash2, Upload, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PageHeader } from "@/components/app/page-header";
import { StatusBadge } from "@/components/documents/status-badge";
import { UploadDialog } from "@/components/documents/upload-dialog";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useAddTag,
  useDeleteDocument,
  useDocuments,
  useRemoveTag,
  useReprocessDocument,
  useTags,
} from "@/hooks/use-documents";
import type { DocumentItem } from "@/lib/types";
import { useWorkspaceStore } from "@/stores/workspace";

const STATUSES = ["uploaded", "extracting", "chunking", "embedding", "ready", "failed"];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function RowTags({ doc, workspaceId }: { doc: DocumentItem; workspaceId: string }) {
  const addTag = useAddTag(workspaceId);
  const removeTag = useRemoveTag(workspaceId);
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const name = value.trim();
    if (!name) return;
    await addTag.mutateAsync({ documentId: doc.id, name });
    setValue("");
    setOpen(false);
  }

  return (
    <div className="flex flex-wrap items-center gap-1">
      {doc.tags.map((t) => (
        <span
          key={t.id}
          className="inline-flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-xs"
        >
          {t.name}
          <button
            type="button"
            aria-label={`Remove tag ${t.name}`}
            className="text-muted-foreground hover:text-destructive"
            onClick={() => removeTag.mutate({ documentId: doc.id, tagId: t.id })}
          >
            <X className="h-3 w-3" />
          </button>
        </span>
      ))}
      {open ? (
        <form onSubmit={submit} className="inline-flex">
          <input
            autoFocus
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onBlur={() => !value && setOpen(false)}
            placeholder="tag…"
            className="h-6 w-20 rounded border border-input bg-background px-1.5 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </form>
      ) : (
        <button
          type="button"
          aria-label="Add tag"
          className="inline-flex items-center rounded-full border border-dashed border-border px-1.5 py-0.5 text-xs text-muted-foreground hover:text-foreground"
          onClick={() => setOpen(true)}
        >
          <Plus className="h-3 w-3" />
        </button>
      )}
    </div>
  );
}

export default function DocumentsPage() {
  const workspaceId = useWorkspaceStore((s) => s.activeId);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [uploadOpen, setUploadOpen] = useState(false);

  const { data: tags } = useTags(workspaceId);
  const { data: docs, isLoading } = useDocuments(workspaceId, {
    search: search || undefined,
    status_filter: statusFilter || undefined,
    tag_id: tagFilter || undefined,
  });
  const del = useDeleteDocument(workspaceId);
  const reprocess = useReprocessDocument(workspaceId);

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

  const hasFilters = Boolean(search || statusFilter || tagFilter);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Knowledge base"
        title="Documents"
        description="Upload the sources DOC-007-AI grounds its answers in. Every file is chunked, embedded, and citable."
        actions={
          <Button onClick={() => setUploadOpen(true)}>
            <Upload className="h-4 w-4" />
            Upload
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1" style={{ minWidth: 220 }}>
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by filename…"
            className="pl-9"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="h-10 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s} className="capitalize">
              {s}
            </option>
          ))}
        </select>
        <select
          value={tagFilter}
          onChange={(e) => setTagFilter(e.target.value)}
          className="h-10 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <option value="">All tags</option>
          {(tags ?? []).map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <Card className="divide-y divide-border overflow-hidden">
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="flex items-center gap-4 px-4 py-3.5">
              <Skeleton className="h-4 w-4 rounded" />
              <Skeleton className="h-4 flex-1" />
              <Skeleton className="h-5 w-16 rounded-full" />
              <Skeleton className="h-4 w-10" />
              <Skeleton className="h-4 w-12" />
            </div>
          ))}
        </Card>
      ) : !docs || docs.length === 0 ? (
        <Card className="flex flex-col items-center gap-3 p-12 text-center">
          <FileText className="h-10 w-10 text-muted-foreground" />
          <div>
            <p className="font-medium">{hasFilters ? "No matching documents" : "No documents yet"}</p>
            <p className="text-sm text-muted-foreground">
              {hasFilters
                ? "Try clearing the search or filters."
                : "Upload a PDF, text, or Markdown file to get started."}
            </p>
          </div>
          {!hasFilters && (
            <Button onClick={() => setUploadOpen(true)}>
              <Upload className="h-4 w-4" />
              Upload your first document
            </Button>
          )}
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-secondary/40 text-left font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Tags</th>
                <th className="px-4 py-3 font-medium">Chunks</th>
                <th className="px-4 py-3 font-medium">Size</th>
                <th className="px-4 py-3 font-medium">Uploaded</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr
                  key={d.id}
                  className="border-b border-border transition-colors last:border-0 hover:bg-secondary/30"
                >
                  <td className="px-4 py-3">
                    <Link
                      href={`/documents/${d.id}`}
                      className="flex items-center gap-2 font-medium hover:text-primary"
                    >
                      <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                      {d.original_filename}
                    </Link>
                    {d.status === "failed" && d.error_message && (
                      <span className="mt-1 block text-xs text-destructive">
                        {d.error_message}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={d.status} />
                  </td>
                  <td className="px-4 py-3">
                    <RowTags doc={d} workspaceId={workspaceId} />
                  </td>
                  <td className="px-4 py-3 font-mono text-xs tabular-nums text-muted-foreground">
                    {d.chunk_count}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs tabular-nums text-muted-foreground">
                    {formatBytes(d.file_size_bytes)}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                    {formatDate(d.created_at)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Reprocess"
                        title="Reprocess"
                        disabled={reprocess.isPending}
                        onClick={() => reprocess.mutate(d.id)}
                      >
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Delete"
                        title="Delete"
                        disabled={del.isPending}
                        onClick={() => del.mutate(d.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <UploadDialog
        workspaceId={workspaceId}
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
      />
    </div>
  );
}
