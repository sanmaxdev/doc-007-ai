"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { useUploadDocument } from "@/hooks/use-documents";
import { ApiError } from "@/lib/api";

export function UploadDialog({
  workspaceId,
  open,
  onClose,
}: {
  workspaceId: string;
  open: boolean;
  onClose: () => void;
}) {
  const upload = useUploadDocument(workspaceId);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  function close() {
    setFile(null);
    setError(null);
    onClose();
  }

  async function submit() {
    if (!file) return;
    setError(null);
    try {
      await upload.mutateAsync(file);
      close();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed. Please try again.");
    }
  }

  return (
    <Dialog open={open} onClose={close}>
      <h2 className="text-lg font-semibold">Upload document</h2>
      <p className="mt-1 text-sm text-muted-foreground">PDF, TXT, or Markdown, up to 25 MB.</p>

      <input
        type="file"
        accept=".pdf,.txt,.md,.markdown,.docx"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        className="mt-4 block w-full rounded-md border border-border p-2 text-sm file:mr-3 file:rounded file:border-0 file:bg-secondary file:px-3 file:py-1 file:text-sm"
      />

      {error && <p className="mt-3 text-sm text-destructive">{error}</p>}

      <div className="mt-6 flex justify-end gap-2">
        <Button variant="outline" onClick={close}>
          Cancel
        </Button>
        <Button onClick={submit} disabled={!file || upload.isPending}>
          {upload.isPending ? "Uploading…" : "Upload"}
        </Button>
      </div>
    </Dialog>
  );
}
