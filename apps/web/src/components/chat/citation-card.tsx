import { FileText } from "lucide-react";

import type { Citation } from "@/lib/types";

export function CitationCard({ citation }: { citation: Citation }) {
  const location = citation.page_number ? `p.${citation.page_number}` : "";
  return (
    <div className="rounded-lg border border-border bg-background/60 p-2.5 text-xs">
      <div className="flex items-center gap-2">
        <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        <span className="font-mono text-primary">[{citation.index}]</span>
        <span className="truncate font-medium">{citation.document_filename}</span>
        {location && <span className="font-mono text-muted-foreground">{location}</span>}
        <span className="ml-auto shrink-0 font-mono tabular-nums text-muted-foreground">
          {citation.score.toFixed(2)}
        </span>
      </div>
      <p className="mt-1.5 line-clamp-3 leading-relaxed text-muted-foreground">
        {citation.snippet}
      </p>
    </div>
  );
}
