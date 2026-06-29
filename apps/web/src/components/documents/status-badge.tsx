import { Badge } from "@/components/ui/badge";
import type { DocumentStatus } from "@/lib/types";

const MAP: Record<DocumentStatus, { label: string; variant: "info" | "success" | "danger" }> = {
  uploaded: { label: "Queued", variant: "info" },
  extracting: { label: "Extracting", variant: "info" },
  chunking: { label: "Chunking", variant: "info" },
  embedding: { label: "Embedding", variant: "info" },
  ready: { label: "Ready", variant: "success" },
  failed: { label: "Failed", variant: "danger" },
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  const { label, variant } = MAP[status];
  return <Badge variant={variant}>{label}</Badge>;
}
