import { FileText } from "lucide-react";

import type { Citation } from "@/lib/types";

export function CitationCard({ citation }: { citation: Citation }) {
  const location = citation.page_number ? `, p.${citation.page_number}` : "";
  return (
    <div className="rounded-md border border-border bg-background p-2.5 text-xs">
      <div className="flex items-center gap-1.5 font-medium">
        <FileText className="h-3.5 w-3.5 shrink-0 text-primary" />
        <span className="truncate">
          [{citation.index}] {citation.document_filename}
          {location}
        </span>
        <span className="ml-auto shrink-0 text-muted-foreground">
          {Math.round(citation.score * 100)}%
        </span>
      </div>
      <p className="mt-1 line-clamp-3 text-muted-foreground">{citation.snippet}</p>
    </div>
  );
}
