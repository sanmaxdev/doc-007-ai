import { Badge } from "@/components/ui/badge";

const MAP: Record<string, { label: string; variant: "success" | "warning" | "info" }> = {
  high: { label: "High confidence", variant: "success" },
  medium: { label: "Medium confidence", variant: "warning" },
  low: { label: "Low confidence", variant: "info" },
};

export function CoverageBadge({ coverage }: { coverage: string }) {
  const entry = MAP[coverage];
  if (!entry) return null;
  return <Badge variant={entry.variant}>{entry.label}</Badge>;
}
