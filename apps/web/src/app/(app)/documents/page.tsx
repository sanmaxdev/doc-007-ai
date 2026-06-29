"use client";

import { FileText, RefreshCw, Trash2, Upload } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { StatusBadge } from "@/components/documents/status-badge";
import { UploadDialog } from "@/components/documents/upload-dialog";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  useDeleteDocument,
  useDocuments,
  useReprocessDocument,
} from "@/hooks/use-documents";
import { useWorkspaceStore } from "@/stores/workspace";

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

export default function DocumentsPage() {
  const workspaceId = useWorkspaceStore((s) => s.activeId);
  const { data: docs, isLoading } = useDocuments(workspaceId);
  const del = useDeleteDocument(workspaceId);
  const reprocess = useReprocessDocument(workspaceId);
  const [uploadOpen, setUploadOpen] = useState(false);

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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Documents</h1>
          <p className="text-sm text-muted-foreground">
            Upload the sources for your knowledge base.
          </p>
        </div>
        <Button onClick={() => setUploadOpen(true)}>
          <Upload className="h-4 w-4" />
          Upload
        </Button>
      </div>

      {isLoading ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : !docs || docs.length === 0 ? (
        <Card className="flex flex-col items-center gap-3 p-12 text-center">
          <FileText className="h-10 w-10 text-muted-foreground" />
          <div>
            <p className="font-medium">No documents yet</p>
            <p className="text-sm text-muted-foreground">
              Upload a PDF, text, or Markdown file to get started.
            </p>
          </div>
          <Button onClick={() => setUploadOpen(true)}>
            <Upload className="h-4 w-4" />
            Upload your first document
          </Button>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-secondary/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Pages</th>
                <th className="px-4 py-3 font-medium">Chunks</th>
                <th className="px-4 py-3 font-medium">Size</th>
                <th className="px-4 py-3 font-medium">Uploaded</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-3">
                    <span className="flex items-center gap-2 font-medium">
                      <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                      {d.original_filename}
                    </span>
                    {d.status === "failed" && d.error_message && (
                      <span className="mt-1 block text-xs text-destructive">
                        {d.error_message}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={d.status} />
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{d.page_count ?? "—"}</td>
                  <td className="px-4 py-3 text-muted-foreground">{d.chunk_count}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {formatBytes(d.file_size_bytes)}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{formatDate(d.created_at)}</td>
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
