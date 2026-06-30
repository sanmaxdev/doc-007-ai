import { Badge } from "@/components/ui/badge";
import type { DocumentStatus } from "@/lib/types";

const MAP: Record<
  DocumentStatus,
  { label: string; variant: "info" | "success" | "danger"; pulse?: boolean }
> = {
  uploaded: { label: "Queued", variant: "info", pulse: true },
  extracting: { label: "Extracting", variant: "info", pulse: true },
  chunking: { label: "Chunking", variant: "info", pulse: true },
  embedding: { label: "Embedding", variant: "info", pulse: true },
  ready: { label: "Ready", variant: "success" },
  failed: { label: "Failed", variant: "danger" },
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  const { label, variant, pulse } = MAP[status];
  return (
    <Badge variant={variant}>
      <span className="relative flex h-1.5 w-1.5">
        {pulse && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-60" />
        )}
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-current" />
      </span>
      {label}
    </Badge>
  );
}
